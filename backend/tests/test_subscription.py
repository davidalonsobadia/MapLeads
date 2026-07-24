"""Tests for the billing SubscriptionService, the GET /subscription endpoint
and the quota / read-only enforcement wired into lead saving and project
creation.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
That user is seeded directly on the session without going through registration,
so it has no subscription until one is lazily created by
``SubscriptionService.get_for_user`` — which is exactly the behavior these tests
also rely on.
"""

from datetime import datetime, timedelta

from app.domains.billing import plans
from app.domains.billing.service import SubscriptionService

PROJECTS = "/api/v1/projects"
SUBSCRIPTION = "/api/v1/subscription"


def _create_project(client, name="Prospects") -> int:
    return client.post(PROJECTS, json={"name": name}).json()["id"]


def _items(n, start=0):
    return [{"place_id": f"p{i}", "name": f"Lead {i}"} for i in range(start, start + n)]


def _get_subscription(db_session, user_id):
    """Resolve (creating if needed) the user's subscription on the shared session."""
    return SubscriptionService(db_session).get_for_user(user_id)


def test_usage_reflects_trial_defaults_and_lead_saving(client, test_user):
    """GET /subscription returns trial defaults; saving leads decrements remaining."""
    response = client.get(SUBSCRIPTION)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == plans.PLAN_TRIAL
    assert body["status"] == plans.STATUS_TRIALING
    assert body["monthly_lead_quota"] == plans.TRIAL_LEAD_QUOTA
    assert body["leads_used"] == 0
    assert body["remaining"] == plans.TRIAL_LEAD_QUOTA
    assert body["trial_days_left"] == plans.TRIAL_PERIOD_DAYS
    assert body["read_only"] is False

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    assert client.post(base, json={"items": _items(2)}).status_code == 201

    body = client.get(SUBSCRIPTION).json()
    assert body["leads_used"] == 2
    assert body["remaining"] == plans.TRIAL_LEAD_QUOTA - 2


def test_only_new_leads_consume_quota(client, test_user, db_session):
    """Duplicates are skipped and never counted against the quota."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    client.post(base, json={"items": _items(2)})
    # Re-saving the same two plus one new: only the new one consumes quota.
    result = client.post(
        base, json={"items": _items(2) + _items(1, start=2)}
    ).json()
    assert [lead["place_id"] for lead in result["saved"]] == ["p2"]
    assert sorted(result["skipped_place_ids"]) == ["p0", "p1"]

    assert client.get(SUBSCRIPTION).json()["leads_used"] == 3


def test_quota_exhausted_blocks_saving_but_not_reading(client, test_user, db_session):
    """Saving up to the quota works; one more new lead returns 403 read-only."""
    sub = _get_subscription(db_session, test_user.id)
    sub.monthly_lead_quota = 2
    db_session.commit()

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    assert client.post(base, json={"items": _items(2)}).status_code == 201

    # The quota is now exhausted: a new lead is rejected and nothing is saved.
    response = client.post(base, json={"items": _items(1, start=2)})
    assert response.status_code == 403
    assert "read-only" in response.json()["detail"]

    # Reads still work; the blocked lead was not persisted.
    listed = client.get(base).json()
    assert {lead["place_id"] for lead in listed} == {"p0", "p1"}

    # And usage reports the account as read-only.
    assert client.get(SUBSCRIPTION).json()["read_only"] is True


def test_all_duplicate_batch_is_allowed_when_quota_exhausted(
    client, test_user, db_session
):
    """A no-op (all-duplicate) save is never blocked, even at the quota."""
    sub = _get_subscription(db_session, test_user.id)
    sub.monthly_lead_quota = 2
    db_session.commit()

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    client.post(base, json={"items": _items(2)})  # fills the quota

    # Re-sending the exact same items saves nothing and must not 403.
    response = client.post(base, json={"items": _items(2)})
    assert response.status_code == 201
    body = response.json()
    assert body["saved"] == []
    assert sorted(body["skipped_place_ids"]) == ["p0", "p1"]


def test_trial_expired_blocks_saving_and_marks_read_only(client, test_user, db_session):
    """An expired trial without a paid plan is read-only for new saves."""
    sub = _get_subscription(db_session, test_user.id)
    sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    sub.period_end = sub.trial_ends_at
    db_session.commit()

    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    response = client.post(base, json={"items": _items(1)})
    assert response.status_code == 403
    assert "trial" in response.json()["detail"].lower()

    body = client.get(SUBSCRIPTION).json()
    assert body["read_only"] is True
    assert body["trial_days_left"] == 0


def test_trial_expired_all_duplicates_not_blocked(client, test_user, db_session):
    """Trial expired + all-duplicate batch must return 201 with saved=[], not 403."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    client.post(base, json={"items": _items(2)})  # save initial batch while valid

    sub = _get_subscription(db_session, test_user.id)
    sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    sub.period_end = sub.trial_ends_at
    db_session.commit()

    # Re-saving the exact same items is a no-op and must not 403.
    response = client.post(base, json={"items": _items(2)})
    assert response.status_code == 201
    assert response.json()["saved"] == []


def test_project_limit_blocks_beyond_plan_allowance(client, test_user, db_session):
    """Creating more active projects than the Basic plan allows is blocked with 403."""
    sub = _get_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_BASIC
    sub.status = plans.STATUS_ACTIVE
    sub.monthly_lead_quota = plans.BASIC.monthly_lead_quota
    db_session.commit()

    assert plans.BASIC.max_active_projects == 1
    # First project fits the limit.
    assert client.post(PROJECTS, json={"name": "First"}).status_code == 201
    # Second exceeds the Basic limit of one active project.
    response = client.post(PROJECTS, json={"name": "Second"})
    assert response.status_code == 403
    assert "plan" in response.json()["detail"].lower()


def test_archiving_frees_a_project_slot(client, test_user, db_session):
    """Only active projects count: archiving one lets the user create another."""
    sub = _get_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_BASIC
    db_session.commit()

    first_id = client.post(PROJECTS, json={"name": "First"}).json()["id"]
    # Archiving the only active project frees the single Basic slot.
    client.patch(f"{PROJECTS}/{first_id}", json={"archived": True})
    assert client.post(PROJECTS, json={"name": "Second"}).status_code == 201


def test_unlimited_plan_allows_many_projects(client, test_user, db_session):
    """A plan with no project limit (Pro) never blocks project creation."""
    sub = _get_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    db_session.commit()

    assert plans.PRO.max_active_projects is None
    for i in range(3):
        assert client.post(PROJECTS, json={"name": f"P{i}"}).status_code == 201
