// ═══════════════════════════════════════════════════════════════════════
//  RedVault – Security Assessment Report Template  (Typst)
//
//  This is the default generic report template. You can customise it
//  for your company by editing this file and replacing banner.png /
//  logo.png in the same folder. See the documentation for details.
// ═══════════════════════════════════════════════════════════════════════

// ─── data ───
#let data      = json(sys.inputs.at("data-path"))
#let findings  = data.at("findings", default: ())
#let asset     = data.at("asset", default: "Target")
#let client    = data.at("client", default: "")
#let from-date = data.at("from", default: "")
#let to-date   = data.at("to", default: "")
#let rpt-date  = data.at("date", default: "")
#let total     = int(data.at("total", default: 0))
#let critical  = int(data.at("critical", default: 0))
#let high      = int(data.at("high", default: 0))
#let medium    = int(data.at("medium", default: 0))
#let low       = int(data.at("low", default: 0))
#let info      = int(data.at("info", default: 0))

// ─── paths ───
#let tpl-dir = sys.inputs.at("tpl-dir", default: ".")

// ═══════════════════════════════════════════════════════════════════════
//  DESIGN TOKENS  (edit these to match your company brand)
// ═══════════════════════════════════════════════════════════════════════

#let brand-dark    = rgb("#1e293b")   // headings, cover title
#let brand-mid     = rgb("#334155")   // subtitles
#let brand-muted   = rgb("#64748b")   // metadata, headers
#let brand-light   = rgb("#f1f5f9")   // table stripes
#let brand-bg      = rgb("#f8fafc")   // light backgrounds

#let sev-color(sev) = {
  let s = lower(sev)
  if s == "critical" { rgb("#b91c1c") }
  else if s == "high"   { rgb("#c2410c") }
  else if s == "medium" { rgb("#d97706") }
  else if s == "low"    { rgb("#2563eb") }
  else if s == "info" or s == "informational" { rgb("#64748b") }
  else { brand-muted }
}

#let sev-bg(sev) = {
  let s = lower(sev)
  if s == "critical" { rgb("#fef2f2") }
  else if s == "high"   { rgb("#f9ece7") }
  else if s == "medium" { rgb("#fffbeb") }
  else if s == "low"    { rgb("#eff6ff") }
  else if s == "info" or s == "informational" { rgb("#f8fafc") }
  else { brand-bg }
}

// Table fill: header row → grey, alternating body rows
#let table-fill(_, row) = {
  if row == 0 { rgb("#eff3f6") }
  else if calc.rem(row, 2) == 0 { brand-light }
  else { white }
}

// ═══════════════════════════════════════════════════════════════════════
//  PAGE SETUP
// ═══════════════════════════════════════════════════════════════════════

#set page(
  paper: "a4",
  margin: (top: 28mm, bottom: 22mm, left: 25mm, right: 25mm),
  header: context {
    let pg = counter(page).get().first()
    if pg > 1 {
      grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        text(9pt, style: "italic", fill: brand-muted)[
          Security Assessment Report – #asset
        ],
        text(9pt, fill: brand-muted)[#counter(page).display()],
      )
    }
  },
)

#set text(font: "Liberation Sans", size: 11pt, fill: black)
#set par(justify: true, leading: 0.65em)
#set heading(numbering: "1.1")

// Consistent medium size for all evidence/finding images
#show figure.where(kind: image): set image(width: 60%)

#show heading.where(level: 1): it => {
  v(8pt)
  text(16pt, weight: "bold", fill: brand-dark)[#it]
  v(4pt)
}
#show heading.where(level: 2): it => {
  v(6pt)
  text(13pt, weight: "bold", fill: brand-dark)[#it]
  v(3pt)
}
#show heading.where(level: 3): it => {
  v(4pt)
  text(11pt, weight: "bold", fill: brand-dark)[#it]
  v(2pt)
}

// Table defaults
#set table(
  stroke: none,
  inset: 7pt,
)
#show table: it => align(center, it)

#show raw.where(block: true): it => block(
  width: 100%,
  fill: brand-light,
  inset: 8pt,
  it,
)

// ═══════════════════════════════════════════════════════════════════════
//  PAGE 1 — COVER
//
//  Customise the cover by replacing banner.png and logo.png in the
//  report_templates/ folder with your company's images.
//    - banner.png → decorative graphic (top-right, ~300pt tall)
//    - logo.png   → company logo (left side, ~85pt tall)
// ═══════════════════════════════════════════════════════════════════════

#place(top + right, dx: 25mm, dy: -28mm)[
  #image(tpl-dir + "/banner.png", height: 300pt)
]
#place(top + left, dy: 200pt)[
  #image(tpl-dir + "/logo.png", height: 85pt)
]

#v(1fr)
#v(1fr)

#align(center)[
  #text(28pt, weight: "bold", fill: brand-dark)[Security Assessment Report]
  #v(10pt)
  #text(20pt, fill: brand-mid)[#asset]
]

#v(1fr)

#set text(10pt, fill: brand-muted)
#grid(
  columns: (auto, auto),
  row-gutter: 5pt,
  column-gutter: 16pt,
  text(weight: "bold")[Prepared for:],      text(fill: brand-muted)[#client],
  text(weight: "bold")[Assessment Period:],  text(fill: brand-muted)[#from-date – #to-date],
  text(weight: "bold")[Report Generated:],   text(fill: brand-muted)[#rpt-date],
)
#set text(11pt, fill: black)

#pagebreak()

// ═══════════════════════════════════════════════════════════════════════
//  PAGE 2 — TABLE OF CONTENTS
// ═══════════════════════════════════════════════════════════════════════

#align(center)[
  #text(16pt, weight: "bold", fill: brand-dark)[Table of Contents]
]
#v(12pt)

#show outline.entry.where(level: 1): it => {
  v(2pt)
  strong(it)
}

#outline(
  title: none,
  indent: 1.5em,
  depth: 3,
)

#pagebreak()

// ═══════════════════════════════════════════════════════════════════════
//  1. EXECUTIVE SUMMARY
// ═══════════════════════════════════════════════════════════════════════

= Executive Summary

This document reflects the findings and conclusions of the security assessment performed on #asset.

A security assessment was conducted during the working days from #from-date to #to-date, with the objective of finding security weaknesses and providing recommendations for mitigating the discovered vulnerabilities.

#if critical > 0 [
  Additionally, #critical critical-severity finding(s) were identified that may lead to full system compromise, data breach, or service disruption. Immediate remediation is recommended.
]

#if high > 0 [
  Additionally, #high high-severity finding(s) were identified that represent a significant risk and should be addressed in the short term.
]

#pagebreak()

// ═══════════════════════════════════════════════════════════════════════
//  2. VULNERABILITIES — SUMMARY
// ═══════════════════════════════════════════════════════════════════════

= Vulnerabilities - Summary

This section enumerates all vulnerabilities that were discovered during the assessment. For each vulnerability, a technical description, along with steps to reproduce, will be given.

Recommendations will also be provided alongside external references and articles that may be used to mitigate the discovered vulnerabilities.

#v(8pt)

#table(
  columns: (auto, auto, 1fr),
  fill: table-fill,
  table.hline(stroke: 0.6pt + black),
  table.header(
    [*Severity*], [*Count*], [*Risk Level*],
  ),
  table.hline(stroke: 0.6pt + black),
  [Critical], [#critical], [Immediate remediation required],
  [High],     [#high],     [Short-term remediation recommended],
  [Medium],   [#medium],   [Planned remediation advised],
  [Low],      [#low],      [Address during regular maintenance],
  [Info],     [#info],     [Informational / best practice],
  table.hline(stroke: 0.6pt + black),
)

#v(12pt)

The following table provides a high-level summary of all findings.

#v(8pt)

#table(
  columns: (auto, 1fr, auto, auto, auto),
  fill: table-fill,
  table.hline(stroke: 0.6pt + black),
  table.header(
    [*ID*], [*Title*], [*Severity*], [*CVSS*], [*State*],
  ),
  table.hline(stroke: 0.6pt + black),
  ..findings.map(f => (
    [V#f.at("num")],
    f.at("title"),
    f.at("severity"),
    f.at("cvss", default: "—"),
    f.at("status"),
  )).flatten(),
  table.hline(stroke: 0.6pt + black),
)

#pagebreak()

// ═══════════════════════════════════════════════════════════════════════
//  3. DETAILED FINDINGS
// ═══════════════════════════════════════════════════════════════════════

= Detailed Findings

#for (i, f) in findings.enumerate() {
  if i > 0 { pagebreak(weak: true) }

  let sev = f.at("severity")

  // Finding title with severity on the right
  block(width: 100%, below: 12pt)[
    #grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      heading(level: 2)[V#f.at("num") – #f.at("title")],
      text(13pt, weight: "bold", fill: sev-color(sev))[#sev],
    )
  ]

  // CVSS score and vector (if available)
  if f.at("cvss", default: "") != "" and f.at("cvss", default: "") != "—" {
    block(width: 100%, below: 6pt)[
      #text(10pt, fill: brand-muted)[
        *CVSS:* #f.at("cvss", default: "")
        #if f.at("cvss-vector", default: "") != "" [
          #h(8pt) *Vector:* #f.at("cvss-vector")
        ]
      ]
    ]
  }

  // Finding content (subsections become 3.x.1, 3.x.2, …)
  block(width: 100%)[
    #eval(f.at("report-content"), mode: "markup")
  ]

  v(14pt)
}

#pagebreak()

// ═══════════════════════════════════════════════════════════════════════
//  4. CONCLUSION
// ═══════════════════════════════════════════════════════════════════════

= Conclusion

This report has documented *#total* finding(s) across the assessed target #asset. The severity distribution is summarised below:

#v(8pt)

#table(
  columns: (auto, auto),
  fill: table-fill,
  table.hline(stroke: 0.6pt + black),
  table.header(
    [*Severity*], [*Count*],
  ),
  table.hline(stroke: 0.6pt + black),
  [Critical], [#critical],
  [High],     [#high],
  [Medium],   [#medium],
  [Low],      [#low],
  [Info],     [#info],
  table.hline(stroke: 0.6pt + black),
)
