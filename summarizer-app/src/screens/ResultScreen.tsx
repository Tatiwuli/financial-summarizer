import { useSummaryStore } from "../state/SummaryStoreTest"
import {
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
  StyleSheet,
  Platform,
} from "react-native"
import {
  OverviewBlockData,
  QaBlockData,
  JudgeBlockData,
  Analyst,
  Question,
  SummaryResult,
} from "../types"
import Clipboard from "@react-native-clipboard/clipboard"
import { Ionicons } from "@expo/vector-icons"

import React, { useState, useRef } from "react" // Import useState for collapsibility
import { useSafeAreaInsets } from "react-native-safe-area-context"

import jsPDF from "jspdf"
import html2canvas from "html2canvas"

import React, { useState } from "react" // Import useState for collapsibility
import { useSafeAreaInsets } from "react-native-safe-area-context"


export const ResultScreen = () => {
  const { result, reset } = useSummaryStore()
  const insets = useSafeAreaInsets()
  const [footerHeight, setFooterHeight] = useState(0)
  const [isMetadataVisible, setIsMetadataVisible] = useState(false) // State for Metadata block visibility

  const reportBlockRef = useRef<any>(null)
  const [reportCopied, setReportCopied] = useState(false)
  const [evalCopied, setEvalCopied] = useState(false)
  const [metaCopied, setMetaCopied] = useState(false)

  // --- Data Extraction (Unchanged) ---
  const overviewBlockEntry = result?.blocks.find(
    (b: any) => b.type === "overview"
  )
  const overviewBlockData = overviewBlockEntry?.data as
    | OverviewBlockData
    | undefined

  const qaBlockEntry = result?.blocks.find((b: any) =>
    b.type.startsWith("q_a_")
  )
  const qaBlockData = qaBlockEntry?.data as QaBlockData | undefined
  const title = result?.title || "Not provided"
  const judgeBlockEntries = (result?.blocks || []).filter(
    (b: any) => b.type === "judge"
  )
  const judgeBlocks: { data: JudgeBlockData; metadata: any }[] =
    judgeBlockEntries.map((entry: any) => ({
      data: entry?.data as JudgeBlockData,
      metadata: entry?.metadata,
    }))

  const summaryMeta = qaBlockEntry?.metadata
  const overviewMeta = overviewBlockEntry?.metadata

  //Helper function to generate a PDF report
  const handleSavePdf = async () => {
    if (Platform.OS !== "web") {
      console.warn("PDF export is currently supported on web only.")
      return
    }
    const node = reportBlockRef.current
    if (!node) {
      console.error("Error generating PDF: report container not found")
      return
    }
    try {
      const canvas = await html2canvas(node as unknown as HTMLElement, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#ffffff",
      })
      const imgData = canvas.toDataURL("image/png")
      const pdf = new jsPDF("p", "px", [canvas.width, canvas.height])
      pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height)
      pdf.save("report.pdf")
    } catch (err) {
      console.error("Error generating PDF:", err)
    }
  }
  // --- Helper Function to write to clipboard ---
  const copyToClipboard = async (
    plainText: string,
    html: string
  ): Promise<boolean> => {
    try {
      if (Platform.OS === "web" && typeof navigator !== "undefined") {
        // @ts-ignore
        if (
          typeof ClipboardItem !== "undefined" &&
          navigator.clipboard?.write
        ) {
          // @ts-ignore
          const item = new ClipboardItem({
            "text/html": new Blob([html], { type: "text/html" }),
            "text/plain": new Blob([plainText], { type: "text/plain" }),
          })
          // @ts-ignore
          await navigator.clipboard.write([item])
          return true
        }
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(plainText)
          return true
        }
      }
      Clipboard.setString(plainText)
      return true
    } catch (_e) {
      return false
    }
  }

  // --- Block-Specific Copy Handlers ---

  const handleCopyReport = async () => {
    const parts: string[] = []
    const htmlParts: string[] = []
    // Title
    parts.push(`# ${title}`)
    htmlParts.push(`<h1>${title}</h1>`)

  const [copiedReport, setCopiedReport] = useState(false)
  const [copiedEvaluation, setCopiedEvaluation] = useState(false)
  const [copiedMetadata, setCopiedMetadata] = useState(false)

  // --- Data Extraction (Unchanged) ---
  const overviewBlockEntry = result?.blocks.find(
    (b: any) => b.type === "overview"
  )
  const overviewBlockData = overviewBlockEntry?.data as
    | OverviewBlockData
    | undefined

  const qaBlockEntry = result?.blocks.find((b: any) =>
    b.type.startsWith("q_a_")
  )
  const qaBlockData = qaBlockEntry?.data as QaBlockData | undefined
  const title = result?.title || "Not provided"
  const judgeBlockEntries = (result?.blocks || []).filter(
    (b: any) => b.type === "judge"
  )
  const judgeBlocks: { data: JudgeBlockData; metadata: any }[] =
    judgeBlockEntries.map((entry: any) => ({
      data: entry?.data as JudgeBlockData,
      metadata: entry?.metadata,
    }))

  const summaryMeta = qaBlockEntry?.metadata
  const overviewMeta = overviewBlockEntry?.metadata

  // --- Helper Function to write to clipboard ---
  const copyToClipboard = (plainText: string, html: string) => {
    if (Platform.OS === "web" && typeof navigator !== "undefined") {
      try {
        // @ts-ignore
        if (
          typeof ClipboardItem !== "undefined" &&
          navigator.clipboard?.write
        ) {
          // @ts-ignore
          const item = new ClipboardItem({
            "text/html": new Blob([html], { type: "text/html" }),
            "text/plain": new Blob([plainText], { type: "text/plain" }),
          })
          // @ts-ignore
          navigator.clipboard.write([item])
          return true
        }
        if (navigator.clipboard?.writeText) {
          navigator.clipboard.writeText(plainText)
          return true
        }
      } catch (_) {
        // Fallback below
      }
    }
    Clipboard.setString(plainText)
    return true
  }

  // --- Block-Specific Copy Handlers ---

  const handleCopyReport = () => {
    const parts: string[] = []
    const htmlParts: string[] = []

    // Title
    parts.push(`# ${title}`)
    htmlParts.push(`<h1>${title}</h1>`)

    // Executives
    if (overviewBlockData?.executives_list?.length) {
      const execs = overviewBlockData.executives_list
        .map(
          (e) =>

            `* **${e.executive_name || "Not provided"}**: ${
              e.role || "Not provided"
            }`

            `* **${e.executive_name || "Not provided"}**: ${e.role || "Not provided"}`

        )
        .join("\n")
      parts.push(`## Executives\n${execs}`)

      htmlParts.push(

        `<h2>Executives</h2><ul>` +
          overviewBlockData.executives_list
            .map(
              (e) =>
                `<li><strong>${e.executive_name || "Not provided"}</strong>: ${
                  e.role || "Not provided"
                }</li>`
        `<h2>Executives</h2>` +
          `<ul>` +
          overviewBlockData.executives_list
            .map(
              (e) =>
                `<li><strong>${e.executive_name || "Not provided"}</strong>: ${e.role || "Not provided"}</li>`

            )
            .join("") +
          `</ul>`
      )

    }
    // Overview
    if (overviewBlockData) {
      parts.push(`## Overview\n${overviewBlockData.overview || "Not provided"}`)
      htmlParts.push(
        `<h2>Overview</h2><p>${
          overviewBlockData.overview || "Not provided"
        }</p>`
      )
      if (overviewBlockData.guidance_outlook) {
        const lines = overviewBlockData.guidance_outlook
          .split(/\r?\n+/)
          .map((l) => l.trim().replace(/^\s*[\-•–—]\s*/, ""))
          .filter(Boolean)
        parts.push(
          `### Guidance & Outlook\n${lines.map((l) => `* ${l}`).join("\n")}`
        )
        htmlParts.push(
          `<h3>Guidance &amp; Outlook</h3><ul>` +
            lines.map((l) => `<li>${l}</li>`).join("") +
            `</ul>`
        )
      }
    }

    }

    // Overview
    if (overviewBlockData) {
      parts.push(`## Overview\n${overviewBlockData.overview || "Not provided"}`)
      htmlParts.push(
        `<h2>Overview</h2><p>${overviewBlockData.overview || "Not provided"}</p>`
      )
      if (overviewBlockData.guidance_outlook) {
        const guidanceItems = overviewBlockData.guidance_outlook
          .split(/\r?\n+/)
          .map((l) => l.trim().replace(/^\s*[\-•–—]\s*/, ""))
          .filter(Boolean)
        const guidance = guidanceItems.map((l) => `* ${l}`).join("\n")
        parts.push(`### Guidance & Outlook\n${guidance}`)
        htmlParts.push(
          `<h3>Guidance &amp; Outlook</h3>` +
            `<ul>` +
            guidanceItems.map((l) => `<li>${l}</li>`).join("") +
            `</ul>`
        )
      }
    }


    // Q&A
    if (qaBlockData) {
      const qaText = qaBlockData.analysts
        .map(
          (a) =>
            `**${a.name || "Not provided"} - ${a.firm || "Not provided"}**\n` +
            a.questions
              .map(
                (q) =>

                  `**Q:** ${q.question || "Not provided"}\n**A:** ${
                    q.answer_summary || "Not provided"
                  }`

                  `**Q:** ${q.question || "Not provided"}\n**A:** ${q.answer_summary || "Not provided"}`

              )
              .join("\n\n")
        )
        .join("\n\n")
      parts.push(`## Q&A\n${qaText}`)


      htmlParts.push(
        `<h2>Q&amp;A</h2>` +
          qaBlockData.analysts
            .map(
              (a) =>
                `<h3>${a.name || "Not provided"} - ${
                  a.firm || "Not provided"
                }</h3>` +
                `<ul>` +
                a.questions
                  .map(
                    (q) =>
                      `<li><strong>Q:</strong> ${
                        q.question || "Not provided"
                      }<br/><strong>A:</strong> ${
                        q.answer_summary || "Not provided"
                      }</li>`
                  )
                  .join("") +
                `</ul>`
            )
            .join("")
      )
    }
    const plain = parts.join("\n\n")
    const html = `<div>${htmlParts.join("")}</div>`
    const ok = await copyToClipboard(plain, html)
    if (ok) {
      setReportCopied(true)
      setTimeout(() => setReportCopied(false), 1500)
    }
  }

  const handleCopyEvaluation = async () => {
    const parts: string[] = []
    const htmlParts: string[] = []
    judgeBlocks.forEach(({ data }) => {
      const oa = data.overall_assessment
      const overall = `**Status:** ${
        oa.overall_passed ? "✅ Passed" : "❌ Failed"
      }\n**Score:** ${oa.passed_criteria}/${oa.total_criteria}\n\n${
        oa.evaluation_summary || "Not provided"
      }`

      const qaHtml = qaBlockData.analysts
        .map((a) => {
          const header = `<h3>Analyst: ${a.name || "Not provided"} - ${a.firm || "Not provided"}</h3>`
          const items =
            `<ul>` +
            a.questions
              .map(
                (q) =>
                  `<li><strong>Q:</strong> ${q.question || "Not provided"}<br/><strong>A:</strong> ${q.answer_summary || "Not provided"}</li>`
              )
              .join("") +
            `</ul>`
          return header + items
        })
        .join("")
      htmlParts.push(`<h2>Q&amp;A</h2>${qaHtml}`)
    }

    const plainText = parts.join("\n\n")
    const html = `<div>${htmlParts.join("")}</div>`
    if (copyToClipboard(plainText, html)) {
      setCopiedReport(true)
      setTimeout(() => setCopiedReport(false), 1500)
    }
  }

  const handleCopyEvaluation = () => {
    const parts: string[] = []
    const htmlParts: string[] = []

    judgeBlocks.forEach(({ data }) => {
      const oa = data.overall_assessment
      const overall = `**Status:** ${oa.overall_passed ? "✅ Passed" : "❌ Failed"}\n**Score:** ${oa.passed_criteria}/${oa.total_criteria}\n\n${oa.evaluation_summary || "Not provided"}`

      parts.push(`## Overall assessment\n${overall}`)

      htmlParts.push(
        `<h2>Overall assessment</h2>` +

          `<p><strong>Status:</strong> ${
            oa.overall_passed ? "✅ Passed" : "❌ Failed"
          }<br/><strong>Score:</strong> ${oa.passed_criteria}/${
            oa.total_criteria
          }</p>` +
          `<p>${oa.evaluation_summary || "Not provided"}</p>`
      )

      if (data.evaluation_results?.some((m) => m.errors?.length)) {
        const header = `| Metric | Error | Transcript Source | Summary Source |\n|---|---|---|---|`
        const rows = data.evaluation_results
          .flatMap((metric) =>
            (metric.errors || []).map(
              (err) =>
                `| ${metric.metric_name || "N/A"} | ${err.error || "N/A"} | ${
                  err.transcript_text || "N/A"
                } | ${err.summary_text || "N/A"} |`
            )
          )
          .join("\n")
        parts.push(`## Evaluation Results\n${header}\n${rows}`)

        const htmlRows = data.evaluation_results
          .flatMap((metric) =>
            (metric.errors || []).map(
              (err) =>
                `<tr><td>${metric.metric_name || "N/A"}</td><td>${
                  err.error || "N/A"
                }</td><td>${err.transcript_text || "N/A"}</td><td>${
                  err.summary_text || "N/A"
                }</td></tr>`
            )
          )
          .join("")
        htmlParts.push(
          `<h2>Evaluation Results</h2>` +
            `<table border="1" cellspacing="0" cellpadding="4">` +
            `<thead><tr><th>Metric</th><th>Error</th><th>Transcript Source</th><th>Summary Source</th></tr></thead>` +
            `<tbody>${htmlRows}</tbody>` +
            `</table>`
        )
      }
    })
    const plain = parts.join("\n\n----------\n\n")
    const html = `<div>${htmlParts.join("<hr/>")}</div>`
    const ok = await copyToClipboard(plain, html)
    if (ok) {
      setEvalCopied(true)
      setTimeout(() => setEvalCopied(false), 1500)
    }
  }

  // Helper function to format seconds as mm:ss
  const formatDuration = (seconds: number | null | undefined): string => {
    if (seconds == null) return "Not provided"
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`
  }

  const handleCopyMetadata = async () => {
    const parts: string[] = []
    const htmlParts: string[] = []
    const durations: string[] = []
    const tokens: string[] = []

    // Calculate total duration
    const totalSeconds =
      (summaryMeta?.time ?? 0) +
      judgeBlocks.reduce(
        (sum, { metadata }) => sum + (metadata?.time ?? 0),
        0
      ) +
      (overviewMeta?.time ?? 0)

    // Durations
    durations.push(
      `**Summarize Q&A duration:** ${formatDuration(summaryMeta?.time)}`
    )
    const htmlDurations: string[] = []
    htmlDurations.push(
      `<li><strong>Summarize Q&amp;A duration:</strong> ${formatDuration(
        summaryMeta?.time
      )}</li>`
    )
    judgeBlocks.forEach(({ metadata }, i) => {
      durations.push(
        `**Evaluating Q&A Summary duration ${i + 1}:** ${formatDuration(
          metadata?.time
        )}`
      )
      htmlDurations.push(
        `<li><strong>Evaluating Q&amp;A Summary duration ${
          i + 1
        }:</strong> ${formatDuration(metadata?.time)}</li>`
      )
    })
    durations.push(
      `**Generate Overview duration:** ${formatDuration(overviewMeta?.time)}`
    )
    htmlDurations.push(
      `<li><strong>Generate Overview duration:</strong> ${formatDuration(
        overviewMeta?.time
      )}</li>`
    )

    // Tokens
    if (summaryMeta) {
      tokens.push(
        `**Summarize Q&A total tokens:** ${
          summaryMeta.input_tokens + summaryMeta.output_tokens || "Not provided"
        }\nModel: ${summaryMeta.model || "Not provided"}\nEffort-level: ${
          summaryMeta.effort_level || "Not provided"
        }\n- Input: ${summaryMeta.input_tokens || "Not provided"}\n- Output: ${
          summaryMeta.output_tokens || "Not provided"
        } ${
          summaryMeta.reasoning_tokens
            ? `(reasoning: ${summaryMeta.reasoning_tokens})`
            : ""
        }`
      )
    }
    const htmlTokens: string[] = []
    if (summaryMeta) {
      htmlTokens.push(
        `<li><strong>Summarize Q&amp;A total tokens:</strong> ${
          (summaryMeta.input_tokens ?? 0) + (summaryMeta.output_tokens ?? 0)
        }</li>`,
        `<li>Model: ${summaryMeta.model || "Not provided"}</li>`,
        `<li>Effort-level: ${summaryMeta.effort_level || "Not provided"}</li>`,
        `<li style="margin-left:16px">- Input: ${
          summaryMeta.input_tokens || "Not provided"
        }</li>`,
        `<li style="margin-left:16px">- Output: ${
          summaryMeta.output_tokens || "Not provided"
        } ${
          summaryMeta.reasoning_tokens
            ? `(reasoning: ${summaryMeta.reasoning_tokens})`
            : ""
        }</li>`
      )
    }
    judgeBlocks.forEach(({ metadata }, i) => {
      if (metadata) {
        tokens.push(
          `**Evaluating Q&A Summary ${i + 1}:**\nModel: ${
            metadata.model || "Not provided"
          }\nEffort-level: ${
            metadata.effort_level || "Not provided"
          }\n- Input: ${metadata.input_tokens || "Not provided"}\n- Output: ${
            metadata.output_tokens || "Not provided"
          }`
        )
        htmlTokens.push(
          `<li><strong>Evaluating Q&amp;A Summary ${i + 1}:</strong></li>`,
          `<li style="margin-left:16px">Model: ${
            metadata.model || "Not provided"
          }</li>`,
          `<li style="margin-left:16px">Effort-level: ${
            metadata.effort_level || "Not provided"
          }</li>`,
          `<li style="margin-left:16px">- Input: ${
            metadata.input_tokens || "Not provided"
          }</li>`,
          `<li style="margin-left:16px">- Output: ${
            metadata.output_tokens || "Not provided"
          }</li>`
        )
      }
    })
    if (overviewMeta) {
      tokens.push(
        `**Generate Overview:**\nModel: ${
          overviewMeta.model || "Not provided"
        }\nEffort-level: ${
          overviewMeta.effort_level || "Not provided"
        }\n- Input: ${overviewMeta.input_tokens || "Not provided"}\n- Output: ${
          overviewMeta.output_tokens || "Not provided"
        } ${
          overviewMeta.reasoning_tokens
            ? `(reasoning: ${overviewMeta.reasoning_tokens})`
            : ""
        }`
      )
      htmlTokens.push(
        `<li><strong>Generate Overview:</strong></li>`,
        `<li style="margin-left:16px">Model: ${
          overviewMeta.model || "Not provided"
        }</li>`,
        `<li style="margin-left:16px">Effort-level: ${
          overviewMeta.effort_level || "Not provided"
        }</li>`,
        `<li style="margin-left:16px">- Input: ${
          overviewMeta.input_tokens || "Not provided"
        }</li>`,
        `<li style="margin-left:16px">- Output: ${
          overviewMeta.output_tokens || "Not provided"
        } ${
          overviewMeta.reasoning_tokens
            ? `(reasoning: ${overviewMeta.reasoning_tokens})`
            : ""
        }</li>`

          `<p><strong>Status:</strong> ${oa.overall_passed ? "✅ Passed" : "❌ Failed"}<br/><strong>Score:</strong> ${oa.passed_criteria}/${oa.total_criteria}</p>` +
          `<p>${oa.evaluation_summary || "Not provided"}</p>`

      )

      if (data.evaluation_results?.some((m) => m.errors?.length)) {
        const rows = data.evaluation_results
          .flatMap((metric) =>
            (metric.errors || []).map(
              (err) =>
                `| ${metric.metric_name || "N/A"} | ${err.error || "N/A"} | ${err.transcript_text || "N/A"} | ${err.summary_text || "N/A"} |`
            )
          )
          .join("\n")
        const table = `| Metric | Error | Transcript Source | Summary Source |\n|---|---|---|---|\n${rows}`
        parts.push(`## Evaluation Results\n${table}`)

        const htmlTable =
          `<h2>Evaluation Results</h2>` +
          `<table border="1" cellspacing="0" cellpadding="4">` +
          `<thead><tr><th>Metric</th><th>Error</th><th>Transcript Source</th><th>Summary Source</th></tr></thead>` +
          `<tbody>` +
          data.evaluation_results
            .map((metric) =>
              (metric.errors || [])
                .map(
                  (err) =>
                    `<tr><td>${metric.metric_name || "N/A"}</td><td>${err.error || "N/A"}</td><td>${err.transcript_text || "N/A"}</td><td>${err.summary_text || "N/A"}</td></tr>`
                )
                .join("")
            )
            .join("") +
          `</tbody></table>`
        htmlParts.push(htmlTable)
      }
    })

    const plainText = parts.join("\n\n----------\n\n")
    const html = `<div>${htmlParts.join("<hr/>")}</div>`
    if (copyToClipboard(plainText, html)) {
      setCopiedEvaluation(true)
      setTimeout(() => setCopiedEvaluation(false), 1500)
    }
  }

  const handleCopyMetadata = () => {
    const parts: string[] = []
    const htmlParts: string[] = []
    const durations: string[] = []
    const tokens: string[] = []

    // Durations (plain)
    durations.push(
      `**Summarize Q&A duration:** ${summaryMeta?.time ?? "Not provided"}`
    )
    judgeBlocks.forEach(({ metadata }, i) => {
      durations.push(
        `**Evaluating Q&A Summary duration ${i + 1}:** ${metadata?.time ?? "Not provided"}`
      )
    })
    durations.push(
      `**Generate Overview duration:** ${overviewMeta?.time ?? "Not provided"}`
    )

    // Tokens (plain)
    if (summaryMeta) {
      tokens.push(
        `**Summarize Q&A total tokens:** ${(summaryMeta.input_tokens ?? 0) + (summaryMeta.output_tokens ?? 0)}\nModel: ${summaryMeta.model || "Not provided"}\nEffort-level:\n- Input: ${summaryMeta.input_tokens ?? "Not provided"}\n- Output: ${summaryMeta.output_tokens ?? "Not provided"}`
      )
    }
    judgeBlocks.forEach(({ metadata }, i) => {
      if (metadata) {
        tokens.push(
          `**Evaluating Q&A Summary ${i + 1}:**\nModel: ${metadata.model || "Not provided"}\nEffort-level:\n- Input: ${metadata.input_tokens || "Not provided"}\n- Output: ${metadata.output_tokens || "Not provided"}`
        )
      }
    })
    if (overviewMeta) {
      tokens.push(
        `**Generate Overview:**\nModel: ${overviewMeta.model || "Not provided"}\nEffort-level:\n- Input: ${overviewMeta.input_tokens || "Not provided"}\n- Output: ${overviewMeta.output_tokens || "Not provided"}`
      )
    }

    parts.push(
      `### Total Duration (${formatDuration(totalSeconds)})\n${durations.join(
        "\n"
      )}`
    )
    parts.push(`### Total Tokens\n${tokens.join("\n\n")}`)

    // HTML counterparts
    const htmlDurations =
      `<h3>Total Duration</h3>` +
      `<ul>` +
      [
        `<li><strong>Summarize Q&amp;A duration:</strong> ${summaryMeta?.time ?? "Not provided"}</li>`,
        ...judgeBlocks.map(
          ({ metadata }, i) =>
            `<li><strong>Evaluating Q&amp;A Summary duration ${i + 1}:</strong> ${metadata?.time ?? "Not provided"}</li>`
        ),
        `<li><strong>Generate Overview duration:</strong> ${overviewMeta?.time ?? "Not provided"}</li>`,
      ].join("") +
      `</ul>`

    const htmlTokensSections: string[] = []
    if (summaryMeta) {
      htmlTokensSections.push(
        `<div><strong>Summarize Q&amp;A total tokens:</strong> ${(summaryMeta.input_tokens ?? 0) + (summaryMeta.output_tokens ?? 0)}<br/>` +
          `Model: ${summaryMeta.model || "Not provided"}<br/>` +
          `Effort-level:<ul>` +
          `<li>Input: ${summaryMeta.input_tokens ?? "Not provided"}</li>` +
          `<li>Output: ${summaryMeta.output_tokens ?? "Not provided"}</li>` +
          `</ul></div>`
      )
    }
    judgeBlocks.forEach(({ metadata }, i) => {
      if (metadata) {
        htmlTokensSections.push(
          `<div><strong>Evaluating Q&amp;A Summary ${i + 1}:</strong><br/>` +
            `Model: ${metadata.model || "Not provided"}<br/>` +
            `Effort-level:<ul>` +
            `<li>Input: ${metadata.input_tokens || "Not provided"}</li>` +
            `<li>Output: ${metadata.output_tokens || "Not provided"}</li>` +
            `</ul></div>`
        )
      }
    })
    if (overviewMeta) {
      htmlTokensSections.push(
        `<div><strong>Generate Overview:</strong><br/>` +
          `Model: ${overviewMeta.model || "Not provided"}<br/>` +
          `Effort-level:<ul>` +
          `<li>Input: ${overviewMeta.input_tokens || "Not provided"}</li>` +
          `<li>Output: ${overviewMeta.output_tokens || "Not provided"}</li>` +
          `</ul></div>`
      )
    }

    const html = `<div>${htmlDurations}<h3>Total Tokens</h3>${htmlTokensSections.join("")}</div>`
    const plainText = parts.join("\n\n")

    if (copyToClipboard(plainText, html)) {
      setCopiedMetadata(true)
      setTimeout(() => setCopiedMetadata(false), 1500)
    }
    parts.push(`### Total Duration\n${durations.join("\n")}`)
    parts.push(`### Total Tokens\n${tokens.join("\n\n")}`)

    const plain = parts.join("\n\n")
    const html = `<div>
      <h3>Total Duration (${formatDuration(totalSeconds)})</h3>
      <ul>${htmlDurations.join("")}</ul>
      <h3>Total Tokens</h3>
      <ul>${htmlTokens.join("")}</ul>
    </div>`
    const ok = await copyToClipboard(plain, html)
    if (ok) {
      setMetaCopied(true)
      setTimeout(() => setMetaCopied(false), 1500)
    }

  }

  if (!result) {
    return (
      <SafeAreaView style={styles.wrapper}>
        <View style={{ padding: 20 }}>
          <Text>No result found.</Text>
          <TouchableOpacity style={styles.resetButton} onPress={reset}>
            <Text style={styles.resetButtonText}>Start Over</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.wrapper}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={[
          styles.container,
          { paddingBottom: (footerHeight || 0) + insets.bottom },
        ]}
      >
        {/* --- Report Block --- */}

        <View style={styles.blockContainer} ref={reportBlockRef}>
          <View style={styles.blockHeader}>
            <Text style={styles.blockTitle}>Report</Text>
            <View style={styles.rightActions}>
              {reportCopied && (
                <Text style={styles.copiedText}>Copied to clipboard!</Text>
              )}
              <TouchableOpacity onPress={handleCopyReport}>
                <Ionicons name="copy-outline" size={30} color="#007AFF" />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={handleSavePdf}
                style={styles.iconButton}
              >
                <Ionicons name="save-outline" size={30} color="rgb(255 0 0)" />
              </TouchableOpacity>
            </View>
          </View>

        <View style={styles.blockContainer}>
          <View style={styles.blockHeader}>
            <Text style={styles.blockTitle}>Report</Text>
            <TouchableOpacity onPress={handleCopyReport}>
              <Ionicons name="copy-outline" size={34} color="#007AFF" />
            </TouchableOpacity>
          </View>
          {copiedReport && (
            <Text style={styles.copiedText}>Copied to the clipboard!</Text>
          )}

          <Text style={styles.h1}>{title}</Text>
          <Text style={styles.h2}>Executives</Text>
          {overviewBlockData?.executives_list?.length ? (
            overviewBlockData.executives_list.map((exec, index) => (
              <Text key={index} style={styles.bulletItem}>
                •{" "}
                <Text style={styles.boldText}>
                  {exec.executive_name || "Not provided"}
                </Text>
                : {exec.role || "Not provided"}
              </Text>
            ))
          ) : (
            <Text style={styles.bodyText}>Not provided</Text>
          )}

          <Text style={styles.h2}>Overview</Text>
          <Text style={styles.bodyText}>
            {overviewBlockData?.overview || "Not provided"}
          </Text>


          <Text style={styles.h3}>Guidance & Outlook</Text>
          {overviewBlockData?.guidance_outlook ? (
            overviewBlockData.guidance_outlook
              .split(/\r?\n+/)
              .map((l) => l.trim().replace(/^\s*[\-•–—]\s*/, ""))
              .filter(Boolean)
              .map((item, index) => (
                <Text key={index} style={styles.bulletItem}>
                  • {item}
                </Text>
              ))
          ) : (
            <Text style={styles.bodyText}>Not provided</Text>
          )}



          <Text style={styles.h3}>Guidance & Outlook</Text>
          {overviewBlockData?.guidance_outlook ? (
            overviewBlockData.guidance_outlook
              .split(/\r?\n+/)
              .map((l) => l.trim().replace(/^\s*[\-•–—]\s*/, ""))
              .filter(Boolean)
              .map((item, index) => (
                <Text key={index} style={styles.bulletItem}>
                  • {item}
                </Text>
              ))
          ) : (
            <Text style={styles.bodyText}>Not provided</Text>
          )}


          <Text style={styles.h2}>Q&A</Text>
          {qaBlockData?.analysts?.length ? (
            qaBlockData.analysts.map((analyst: Analyst, index: number) => (
              <View key={index} style={styles.analystContainer}>
                <Text style={styles.analystName}>
                  {analyst.name || "Not provided"} -{" "}
                  {analyst.firm || "Not provided"}
                </Text>
                {analyst.questions.map((q: Question, qIndex: number) => (
                  <View key={qIndex} style={styles.questionContainer}>
                    <Text style={styles.bodyText}>
                      <Text style={styles.boldText}>Q:</Text>{" "}
                      {q.question || "Not provided"}
                    </Text>
                    <Text style={styles.bodyText}>
                      <Text style={styles.boldText}>A:</Text>{" "}
                      {q.answer_summary || "Not provided"}
                    </Text>
                  </View>
                ))}
              </View>
            ))
          ) : (
            <Text style={styles.bodyText}>Not provided</Text>
          )}
        </View>

        <View style={styles.divider} />

        {/* --- Evaluation Block --- */}
        <View style={styles.blockContainer}>
          <View style={styles.blockHeader}>
            <Text style={styles.blockTitle}>Evaluation</Text>

            <View style={styles.rightActions}>
              {evalCopied && (
                <Text style={styles.copiedText}>Copied to clipboard!</Text>
              )}
              <TouchableOpacity onPress={handleCopyEvaluation}>
                <Ionicons name="copy-outline" size={30} color="#007AFF" />
              </TouchableOpacity>
            </View>
          </View>

            <TouchableOpacity onPress={handleCopyEvaluation}>
              <Ionicons name="copy-outline" size={34} color="#007AFF" />
            </TouchableOpacity>
          </View>
          {copiedEvaluation && (
            <Text style={styles.copiedText}>Copied to the clipboard!</Text>
          )}

          {judgeBlocks.map(({ data }, idx) => (
            <View key={`judge-${idx}`}>
              <Text style={styles.h2}>Evaluation Results</Text>
              {data.evaluation_results?.some((m) => m.errors?.length) ? (
                <View style={{ marginVertical: 12 }}>
                  <View style={styles.tableHeaderRow}>
                    <Text style={[styles.tableHeaderCell, { flex: 0.8 }]}>
                      Metric
                    </Text>
                    <Text style={[styles.tableHeaderCell, { flex: 1.2 }]}>
                      Error
                    </Text>
                    <Text style={[styles.tableHeaderCell, { flex: 1 }]}>
                      Transcript Source
                    </Text>
                    <Text style={[styles.tableHeaderCell, { flex: 1 }]}>
                      Summary Source
                    </Text>
                  </View>
                  {data.evaluation_results.map((metric, mi) =>
                    (metric.errors || []).map((err, ei) => (
                      <View key={`${mi}-${ei}`} style={styles.tableRow}>
                        <Text style={[styles.tableCell, { flex: 0.8 }]}>
                          {metric.metric_name || "N/A"}
                        </Text>
                        <Text style={[styles.tableCell, { flex: 1.2 }]}>
                          {err.error || "N/A"}
                        </Text>
                        <Text style={[styles.tableCell, { flex: 1 }]}>
                          {err.transcript_text || "N/A"}
                        </Text>
                        <Text style={[styles.tableCell, { flex: 1 }]}>
                          {err.summary_text || "N/A"}
                        </Text>
                      </View>
                    ))
                  )}
                </View>
              ) : (
                <Text style={styles.bodyText}>No evaluation errors found.</Text>
              )}
              <Text style={styles.h2}>Overall assessment</Text>
              <Text style={styles.bodyText}>
                {data.overall_assessment.overall_passed
                  ? "✅ Passed"
                  : "❌ Failed"}{" "}
                <Text style={styles.boldText}>
                  ({data.overall_assessment.passed_criteria || 0}/
                  {data.overall_assessment.total_criteria || 0})
                </Text>
              </Text>
              <Text style={styles.bodyText}>
                {data.overall_assessment.evaluation_summary || "Not provided"}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.divider} />

        {/* --- Metadata Block (Collapsible) --- */}
        <View style={styles.blockContainer}>
          <TouchableOpacity
            style={styles.blockHeader}
            onPress={() => setIsMetadataVisible(!isMetadataVisible)}
          >
            <Text style={styles.blockTitle}>Metadata</Text>

            
            <View style={styles.rightActions}>
              {metaCopied && (
                <Text style={styles.copiedText}>Copied to clipboard!</Text>
              )}

            <View style={{ flexDirection: "row", alignItems: "center" }}>

              <TouchableOpacity
                onPress={handleCopyMetadata}
                style={{ marginRight: 8 }}
              >

                <Ionicons name="copy-outline" size={30} color="#007AFF" />

                <Ionicons name="copy-outline" size={34} color="#007AFF" />

              </TouchableOpacity>
              <Ionicons
                name={
                  isMetadataVisible
                    ? "chevron-up-outline"
                    : "chevron-down-outline"
                }

                size={30}

                size={24}

                color="#3C3C43"
              />
            </View>
          </TouchableOpacity>

          {copiedMetadata && (
            <Text style={styles.copiedText}>Copied to the clipboard!</Text>
          )}
          {isMetadataVisible && (
            <View style={{ marginTop: 10 }}>
              {(() => {
                const totalSeconds =
                  (summaryMeta?.time ?? 0) +
                  judgeBlocks.reduce(
                    (sum, { metadata }) => sum + (metadata?.time ?? 0),
                    0
                  ) +
                  (overviewMeta?.time ?? 0)
                return (
                  <Text style={styles.h3}>
                    Total Duration ({formatDuration(totalSeconds)})
                  </Text>
                )
              })()}
              <Text style={styles.bodyText}>
                <Text style={styles.boldText}>Summarize Q&A duration:</Text>{" "}
                {formatDuration(summaryMeta?.time)}
              </Text>
              {judgeBlocks.map(({ metadata }, i) => (
                <Text key={i} style={styles.bodyText}>
                  <Text style={styles.boldText}>
                    Evaluating Q&A Summary duration {i + 1}:
                  </Text>{" "}
                  {formatDuration(metadata?.time)}
                </Text>
              ))}
              <Text style={styles.bodyText}>
                <Text style={styles.boldText}>Generate Overview duration:</Text>{" "}
                {formatDuration(overviewMeta?.time)}
              </Text>

              <Text style={styles.h3}>Total Tokens</Text>
              {/* Summarize Q&A Tokens */}
              <View style={styles.metadataSection}>
                <Text style={styles.bodyText}>
                  <Text style={styles.boldText}>
                    Summarize Q&A total tokens:
                  </Text>{" "}
                  {(summaryMeta?.input_tokens ?? 0) +
                    (summaryMeta?.output_tokens ?? 0) || "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Model: {summaryMeta?.model ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Effort-level: {summaryMeta?.effort_level ?? "Not provided"}
                </Text>
                <Text style={styles.metadataNested}>
                  - Input: {summaryMeta?.input_tokens ?? "Not provided"}
                </Text>
                <Text style={styles.metadataNested}>
                  - Output: {summaryMeta?.output_tokens ?? "Not provided"}{" "}
                  {summaryMeta?.reasoning_tokens
                    ? `(reasoning: ${summaryMeta.reasoning_tokens})`
                    : ""}
                </Text>
              </View>
              {/* Evaluating Q&A Tokens */}
              {judgeBlocks.map(({ metadata }, i) => (
                <View key={i} style={styles.metadataSection}>
                  <Text style={styles.bodyText}>
                    <Text style={styles.boldText}>
                      Evaluating Q&A Summary {i + 1}:
                    </Text>
                  </Text>
                  <Text style={styles.metadataDetail}>
                    Model: {metadata?.model ?? "Not provided"}
                  </Text>
                  <Text style={styles.metadataDetail}>
                    Effort-level: {metadata?.effort_level ?? "Not provided"}
                  </Text>
                  <Text style={styles.metadataNested}>
                    - Input: {metadata?.input_tokens ?? "Not provided"}
                  </Text>
                  <Text style={styles.metadataNested}>
                    - Output: {metadata?.output_tokens ?? "Not provided"}
                  </Text>
                </View>
              ))}
              {/* Generate Overview Tokens */}
              <View style={styles.metadataSection}>
                <Text style={styles.bodyText}>
                  <Text style={styles.boldText}>Generate Overview:</Text>
                </Text>
                <Text style={styles.metadataDetail}>
                  Model: {overviewMeta?.model ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Effort-level: {overviewMeta?.effort_level ?? "Not provided"}
                </Text>
                <Text style={styles.metadataNested}>
                  - Input: {overviewMeta?.input_tokens ?? "Not provided"}
                </Text>
                <Text style={styles.metadataNested}>
                  - Output: {overviewMeta?.output_tokens ?? "Not provided"}{" "}
                  {overviewMeta?.reasoning_tokens
                    ? `(reasoning: ${overviewMeta.reasoning_tokens})`
                    : ""}
                </Text>
              </View>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Footer (Unchanged) */}
      <View
        style={styles.footer}
        onLayout={(e) => setFooterHeight(e.nativeEvent.layout.height)}
      >
        <TouchableOpacity style={styles.resetButton} onPress={reset}>
          <Text style={styles.resetButtonText}>Start Over</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: "#F2F2F7" },
  container: {
    padding: 15,
  },
  blockContainer: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#E5E5EA",
  },
  blockHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  blockTitle: {
    fontSize: 22,
    fontWeight: "bold",
  },

  rightActions: {
    flexDirection: "row",
    alignItems: "center",
  },
  copiedText: {
    color: "#34C759",
    marginRight: 10,
    fontSize: 14,
  },
  iconButton: {
    marginLeft: 12,
  },

  copiedText: {
    alignSelf: "flex-end",
    marginTop: -6,
    marginBottom: 6,
    color: "rgb(0 0 0)",
    fontSize: 14,
  },

  h1: { fontSize: 26, fontWeight: "bold", marginBottom: 15 },
  h2: { fontSize: 20, fontWeight: "600", marginTop: 15, marginBottom: 8 },
  h3: { fontSize: 18, fontWeight: "600", marginTop: 12, marginBottom: 6 },
  bodyText: { fontSize: 16, lineHeight: 24, color: "#3C3C43", marginBottom: 5 },
  bulletItem: {
    fontSize: 16,
    lineHeight: 24,
    color: "#3C3C43",
    marginLeft: 10,
  },
  boldText: { fontWeight: "bold" },
  divider: {
    height: 1,
    backgroundColor: "#E5E5EA",
    marginVertical: 15,
  },
  analystContainer: { marginBottom: 15 },
  analystName: { fontSize: 16, fontWeight: "bold", marginBottom: 5 },
  questionContainer: {
    marginLeft: 10,
    marginBottom: 10,
    paddingLeft: 5,
    borderLeftWidth: 2,
    borderLeftColor: "#E5E5EA",
  },
  metadataSection: {
    marginTop: 8,
    marginBottom: 8,
  },
  metadataDetail: {
    fontSize: 15,
    lineHeight: 22,
    color: "#3C3C43",
    marginLeft: 10,
  },
  metadataNested: {
    fontSize: 15,
    lineHeight: 22,
    color: "#555555",
    marginLeft: 20,
  },
  footer: {
    padding: 20,
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#E5E5EA",
    alignItems: "center",
  },
  resetButton: {
    backgroundColor: "#007AFF",
    borderRadius: 12,
    paddingVertical: 15,
    paddingHorizontal: 20,
    width: "100%",
    alignItems: "center",
  },
  resetButtonText: { color: "#FFFFFF", fontSize: 18, fontWeight: "600" },
  // Table Styles
  tableHeaderRow: {
    flexDirection: "row",
    backgroundColor: "#F2F2F7",
    padding: 8,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
  },
  tableHeaderCell: {
    fontSize: 14,
    fontWeight: "700",
    color: "#000000",
  },
  tableRow: {
    flexDirection: "row",
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E5EA",
  },
  tableCell: {
    fontSize: 14,
    color: "#3C3C43",
  },
})
