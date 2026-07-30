"use client"

// Client-side PDF export for the masked anonymous-search results (#try-page).
//
// Anonymous results carry no phone/website/coordinates at the type level, so
// generating the PDF straight from `results` cannot leak hidden fields. jsPDF
// is imported dynamically so its bundle cost is only paid when a visitor
// actually clicks export.

import { useState } from "react"
import { useTranslations } from "next-intl"
import { Download, Loader2 } from "lucide-react"

import type { AnonymousSearchResult } from "@/lib/types"
import { formatCategory } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface ExportPdfButtonProps {
  results: AnonymousSearchResult[]
  hiddenCount: number
}

export function ExportPdfButton({ results, hiddenCount }: ExportPdfButtonProps) {
  const t = useTranslations("anonymousSearch.results")
  const tItem = useTranslations("anonymousSearch.item")
  const tCta = useTranslations("anonymousSearch.cta")
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const { jsPDF } = await import("jspdf")
      const doc = new jsPDF()
      const marginX = 14
      let y = 20

      doc.setFontSize(16)
      doc.text("MapLeads", marginX, y)
      y += 8
      doc.setFontSize(10)
      doc.text(new Date().toLocaleDateString(), marginX, y)
      y += 10

      doc.setFontSize(12)
      for (const result of results) {
        if (y > 270) {
          doc.addPage()
          y = 20
        }
        doc.setFont("helvetica", "bold")
        doc.text(result.name ?? tItem("unnamed"), marginX, y)
        y += 6
        doc.setFont("helvetica", "normal")
        const category = formatCategory(result.category)
        if (category) {
          doc.text(category, marginX, y)
          y += 6
        }
        if (result.address) {
          doc.text(result.address, marginX, y)
          y += 6
        }
        y += 4
      }

      if (hiddenCount > 0) {
        if (y > 270) {
          doc.addPage()
          y = 20
        }
        doc.setFont("helvetica", "italic")
        doc.text(tCta("hiddenResults", { count: hiddenCount }), marginX, y, {
          maxWidth: 180,
        })
      }

      doc.save("mapleads-search-results.pdf")
    } finally {
      setExporting(false)
    }
  }

  return (
    <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting}>
      {exporting ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <Download className="mr-2 h-4 w-4" />
      )}
      {t("exportPdf")}
    </Button>
  )
}
