"""Tests for the billing subscription service, quota and read-only enforcement.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``),
which has no subscription seeded: the service provisions a trial on first use.
Tests that need a different plan/state adjust the subscription row directly on
the session.
"""

from datetime import datetime, timedelta

from app.domains.billing import plans
from app.domains.billing.models import Subscription
from app.domains.billing.service import SubscriptionService

SUBSCRIPTION = "/api/v1/subscription"
PROJECTS = "/api/v1/projects"


def _create_project(client, name="Prospects") -> int:
    return client.post(PROJECTS, json={"name": name}).json()["id"]


def _items(n, prefix="p"):
    return [{"place_id": f"{prefix}{i}", "name": f"Lead {i}"} for i in range(n)]


def _get_subscription(db_session, user_id) -> Subscription:
    return db_session.query(Subscription).filter_by(user_id=user_id).first()


def test_get_subscription_reports_trial_usage(client, test_user):
    """A fresh user gets a provisioned trial with full remaining quota."""
    response = client.get(SUBSCRIPTION)
    assert response.status_code == 200
    body = response.json()

    assert body["plan"] == plans.PLAN_TRIAL
    assert body["leads_used"] == 0
    assert body["monthly_lead_quota"] == plans.TRIAL_LEAD_QUOTA
    assert body["remaining"] == plans.TRIAL_LEAD_QUOTA
    assert body["read_only"] is False
    # trial_days_left is the whole trial window for a just-created trial.
    assert body["trial_days_left"] == plans.TRIAL_PERIOD_DAYS
    assert body["trial_ends_at"] is not None


def test_saving_leads_decrements_remaining_by_new_count(client, test_user, db_session):
    """Remaining drops by the number of newly-saved (non-duplicate) leads."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    client.post(base, json={"items": _items(3)})
    body = client.get(SUBSCRIPTION).json()
    assert body["leads_used"] == 3
    assert body["remaining"] == plans.TRIAL_LEAD_QUOTA - 3


def test_duplicates_do_not_consume_quota(client, test_user):
    """Re-saving already-saved place_ids consumes no quota."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    client.post(base, json={"items": _items(2)})
    # re-save the same two + one new -> only one new counts
    client.post(base, json={"items": _items(3)})

    body = client.get(SUBSCRIPTION).json()
    assert body["leads_used"] == 3
    assert body["remaining"] == plans.TRIAL_LEAD_QUOTA - 3


def test_quota_exhaustion_blocks_further_saves(client, test_user, db_session):
    """Save up to quota, then one more -> 403 read-only and nothing saved."""
    # Shrink the quota so the test does not need hundreds of items.
    sub = _get_subscription(db_session, test_user.id)
    if sub is None:
        sub = SubscriptionService(db_session).get_for_user(test_user.id)
    sub.monthly_lead_quota = 2
    db_session.commit()

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    # exactly up to quota is allowed
    assert client.post(base, json={"items": _items(2)}).status_code == 201

    # the account is now read-only
    usage = client.get(SUBSCRIPTION).json()
    assert usage["remaining"] == 0
    assert usage["read_only"] is True

    # one more is blocked with 403 and saves nothing
    response = client.post(base, json={"items": _items(1, prefix="q")})
    assert response.status_code == 403
    assert "read-only" in response.json()["detail"].lower()
    assert len(client.get(base).json()) == 2  # unchanged


def test_reads_and_searches_still_work_when_read_only(client, test_user, db_session):
    """Read-only blocks saving new leads but not listing them."""
    sub = SubscriptionService(db_session).get_for_user(test_user.id)
    sub.monthly_lead_quota = 1
    db_session.commit()

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    client.post(base, json={"items": _items(1)})

    # saving another new lead is blocked...
    assert client.post(base, json={"items": _items(1, prefix="z")}).status_code == 403
    # ...but listing the existing leads still works
    assert client.get(base).status_code == 200
    assert len(client.get(base).json()) == 1


def test_trial_expired_makes_account_read_only(client, test_user, db_session):
    """An expired trial with no paid plan is read-only for lead saving."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    # push the trial into the past
    sub = _get_subscription(db_session, test_user.id)
    sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    sub.period_end = sub.trial_ends_at
    db_session.commit()

    usage = client.get(SUBSCRIPTION).json()
    assert usage["read_only"] is True
    assert usage["trial_days_left"] == 0

    response = client.post(base, json={"items": _items(1)})
    assert response.status_code == 403
    assert "trial" in response.json()["detail"].lower()


def test_active_paid_plan_is_not_read_only_after_trial_window(
    client, test_user, db_session
):
    """Upgrading to a paid plan lifts the expired-trial read-only state."""
    sub = SubscriptionService(db_session).get_for_user(test_user.id)
    sub.plan = plans.PLAN_BASIC
    sub.status = plans.STATUS_ACTIVE
    sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    usage = client.get(SUBSCRIPTION).json()
    assert usage["plan"] == plans.PLAN_BASIC
    assert usage["read_only"] is False
    assert usage["trial_days_left"] is None  # not a trial anymore

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    assert client.post(base, json={"items": _items(1)}).status_code == 201


def test_project_limit_blocks_second_project_on_basic(client, test_user, db_session):
    """The Basic plan allows a single active project; a second is blocked with 403."""
    sub = SubscriptionService(db_session).get_for_user(test_user.id)
    sub.plan = plans.PLAN_BASIC
    sub.status = plans.STATUS_ACTIVE
    db_session.commit()

    assert client.post(PROJECTS, json={"name": "First"}).status_code == 201

    response = client.post(PROJECTS, json={"name": "Second"})
    assert response.status_code == 403
    assert "project" in response.json()["detail"].lower()


def test_archived_projects_do_not_count_toward_limit(client, test_user, db_session):
    """Archiving a project frees a slot under the plan's active-project limit."""
    sub = SubscriptionService(db_session).get_for_user(test_user.id)
    sub.plan = plans.PLAN_BASIC
    sub.status = plans.STATUS_ACTIVE
    db_session.commit()

    first_id = client.post(PROJECTS, json={"name": "First"}).json()["id"]
    # second is blocked while the first is active
    assert client.post(PROJECTS, json={"name": "Second"}).status_code == 403

    # archive the first, then the second is allowed
    client.patch(f"{PROJECTS}/{first_id}", json={"archived": True})
    assert client.post(PROJECTS, json={"name": "Second"}).status_code == 201


def test_pro_plan_allows_unlimited_projects(client, test_user, db_session):
    """A plan with no project limit (Pro) permits many active projects."""
    sub = SubscriptionService(db_session).get_for_user(test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    db_session.commit()

    for name in ("A", "B", "C"):
        assert client.post(PROJECTS, json={"name": name}).status_code == 201
