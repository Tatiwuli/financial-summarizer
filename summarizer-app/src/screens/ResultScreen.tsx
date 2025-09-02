import { useSummaryStore } from "../state/SummaryStore"
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
  QABlock,
  QABlockByTopic,
  JudgeBlockData,
} from "../types"
import Clipboard from "@react-native-clipboard/clipboard"
import { Ionicons } from "@expo/vector-icons"
import React, { useState, useRef, useEffect } from "react"
import { Animated } from "react-native"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { EarningsResult } from "../components/specific/EarningsResult"
import { ConferenceResult } from "../components/specific/ConferenceResult"
import { JudgeEvaluation } from "../components/results/common/JudgeEvaluation"

// @ts-ignore
import pdfMake from "pdfmake/build/pdfmake"

// --- Start of PDF Setup ---
// This entire block should be at the top of your file, outside the component.

// 1. Use 'import * as' to correctly import the CJS-style font module.
import * as pdfFonts from "pdfmake/build/vfs_fonts"

// 2. Assign the imported font object directly to pdfMake's vfs.
// We cast pdfFonts to any here to match the vfs property's expected type.
;(pdfMake as any).vfs = pdfFonts as any

export const ResultScreen = () => {
  const {
    result,
    reset,
    stage,
    percentComplete,
    stages,
    currentCallType,
    validation,
  } = useSummaryStore()
  const insets = useSafeAreaInsets()
  const [footerHeight, setFooterHeight] = useState(0)

  const reportBlockRef = useRef<any>(null)
  const spinValue = useRef(new Animated.Value(0)).current

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  })
  const [reportCopied, setReportCopied] = useState(false)
  const [evalCopied, setEvalCopied] = useState(false)
  const [metaCopied, setMetaCopied] = useState(false)
  const [isMetadataVisible, setIsMetadataVisible] = useState(false)

  const [pdfMessage, setPdfMessage] = useState<string | null>(null)

  //Get the results
  const overviewBlockEntry = result?.blocks.find(
    (b: any) => b.type === "overview"
  )
  const overviewBlockData = overviewBlockEntry?.data as
    | OverviewBlockData
    | undefined

  const qaBlockEntry = result?.blocks.find((b: any) =>
    b.type.startsWith("q_a_")
  )
  const qaEarnings = qaBlockEntry?.data as QABlock | undefined
  const qaConference = qaBlockEntry?.data as QABlockByTopic | undefined

  const resolvedCallType: "earnings" | "conference" =
    (currentCallType as any) ||
    ((String(result?.call_type || "")
      .toLowerCase()
      .includes("earn")
      ? "earnings"
      : "conference") as any)

  const title = result?.title || "Untitled"
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

  // Spinning animation for loading
  useEffect(() => {
    const shouldSpin =
      (stages && stages["summary_evaluation"] === "processing") ||
      ((!judgeBlocks || judgeBlocks.length === 0) &&
        (!stages || stages["summary_evaluation"] !== "failed"))

    if (shouldSpin) {
      const spinAnimation = Animated.loop(
        Animated.timing(spinValue, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        })
      )
      spinAnimation.start()
      return () => spinAnimation.stop()
    }
  }, [stages, spinValue, judgeBlocks])

  // Helper function to generate a PDF report (text-preserving via browser print)
  const handleSavePdf = async () => {
    if (Platform.OS !== "web") {
      console.warn("PDF export is currently supported on web only.")
      return
    }

    try {
      setPdfMessage("Generating PDF...")

      const titleText = title || "Report"

      const content: any[] = []
      content.push({ text: titleText, style: "header", margin: [0, 0, 0, 8] })

      // Executives
      content.push({
        text: "Executives",
        style: "subheader",
        margin: [0, 10, 0, 4],
      })
      if (overviewBlockData?.executives_list?.length) {
        content.push({
          ul: overviewBlockData.executives_list.map(
            (e) =>
              `${e.executive_name || "Not provided"}: ${e.role || "Not provided"}`
          ),
          margin: [0, 0, 0, 6],
        })
      } else {
        content.push({ text: "Not provided", style: "text" })
      }

      // Overview
      content.push({
        text: "Overview",
        style: "subheader",
        margin: [0, 10, 0, 4],
      })
      content.push({ text: overviewBlockData?.overview || "Not provided" })

      // Guidance & Outlook
      content.push({
        text: "Guidance & Outlook",
        style: "subheader",
        margin: [0, 10, 0, 4],
      })
      if (overviewBlockData?.guidance_outlook?.length) {
        const grouped: Record<
          string,
          { metric_name: string; metric_description: string }[]
        > = {}
        overviewBlockData.guidance_outlook.forEach((item) => {
          const key = item.period_label || "Not provided"
          if (!grouped[key]) grouped[key] = []
          grouped[key].push({
            metric_name: item.metric_name || "Not provided",
            metric_description: item.metric_description || "Not provided",
          })
        })
        Object.entries(grouped).forEach(([period, rows]) => {
          content.push({ text: period, bold: true, margin: [0, 4, 0, 2] })
          content.push({
            ul: rows.map((r) => `${r.metric_name}: ${r.metric_description}`),
          })
        })
      } else {
        content.push({ text: "Overview unavailable", color: "#666" })
      }

      // Q&A
      content.push({ text: "Q&A", style: "subheader", margin: [0, 10, 0, 4] })
      if (resolvedCallType === "earnings") {
        if (qaEarnings?.analysts?.length) {
          qaEarnings.analysts.forEach((a) => {
            content.push({
              text: `${a.name || "Not provided"} - ${a.firm || "Not provided"}`,
              bold: true,
              margin: [0, 6, 0, 2],
            })
            const items: any[] = []
            a.questions.forEach((q: any) => {
              items.push({
                text: [
                  { text: "Q: ", bold: true, color: "#1a365d" },
                  {
                    text: q.question || "Not provided",
                    bold: true,
                    color: "#1a365d",
                  },
                ],
                margin: [0, 0, 0, 4],
              })
              if (Array.isArray(q.answers) && q.answers.length > 0) {
                q.answers.forEach((ans: any) => {
                  items.push({
                    text: [
                      { text: "A ", color: "#000000" },
                      { text: `(${ans.executive})`, color: "#000000" },
                    ],
                    margin: [0, 2, 0, 0],
                  })
                  ;(ans.answer_summary || []).forEach((p: string) => {
                    items.push({ text: `• ${p}`, margin: [0, 8, 0, 0] })
                  })
                })
              } else if (Array.isArray(q.answer_summary)) {
                items.push({
                  text: [{ text: "A:", color: "#000000" }],
                  margin: [0, 2, 0, 0],
                })
                q.answer_summary.forEach((p: string) =>
                  items.push({ text: `• ${p}`, margin: [0, 8, 0, 0] })
                )
              } else {
                items.push({
                  text: [
                    { text: "A: ", color: "#000000" },
                    {
                      text: q.answer_summary || "Not provided",
                      color: "#000000",
                    },
                  ],
                })
              }
            })
            content.push(...items)
          })
        } else {
          content.push({ text: "Not provided" })
        }
      } else {
        // conference: topics
        if (qaConference?.topics?.length) {
          qaConference.topics.forEach((t) => {
            content.push({
              text: t.topic || "Untitled topic",
              bold: true,
              margin: [0, 6, 0, 2],
            })
            t.question_answers.forEach((analyst) => {
              content.push({
                text: `${analyst.name || "Not provided"} - ${analyst.firm || "Not provided"}`,
                bold: true,
                margin: [0, 4, 0, 2],
              })
              const items: any[] = []
              analyst.questions.forEach((q: any) => {
                items.push({
                  text: [
                    { text: "Q: ", bold: true, color: "#1a365d" },
                    {
                      text: q.question || "Not provided",
                      bold: true,
                      color: "#1a365d",
                    },
                  ],
                  margin: [0, 0, 0, 4],
                })
                if (Array.isArray(q.answers) && q.answers.length > 0) {
                  q.answers.forEach((ans: any) => {
                    items.push({
                      text: [
                        { text: "A ", bold: true, color: "#000000" },
                        { text: `(${ans.executive})`, color: "#000000" },
                      ],
                      margin: [0, 2, 0, 0],
                    })
                    ;(ans.answer_summary || []).forEach((p: string) => {
                      items.push({ text: `• ${p}`, margin: [0, 8, 0, 0] })
                    })
                  })
                } else if (Array.isArray(q.answer_summary)) {
                  items.push({
                    text: [{ text: "A:", color: "#000000" }],
                    margin: [0, 2, 0, 0],
                  })
                  q.answer_summary.forEach((p: string) =>
                    items.push({ text: `• ${p}`, margin: [0, 8, 0, 0] })
                  )
                } else {
                  items.push({
                    text: [
                      { text: "A: ", bold: true, color: "#000000" },
                      {
                        text: q.answer_summary || "Not provided",
                        color: "#000000",
                      },
                    ],
                  })
                }
              })
              content.push(...items)
            })
          })
        } else {
          content.push({ text: "Not provided" })
        }
      }

      const docDefinition: any = {
        pageMargins: [40, 40, 40, 40],
        content,
        styles: {
          header: { fontSize: 18, bold: true },
          subheader: { fontSize: 14, bold: true },
          text: { fontSize: 11 },
        },
        defaultStyle: { fontSize: 11 },
      }

      await new Promise((resolve) => setTimeout(resolve, 0))

      // Generate filename based on original file
      const originalFilename = validation?.filename || "document"
      const baseName = originalFilename.replace(/\.pdf$/i, "") // Remove .pdf extension
      const summaryFilename = `${baseName}_Summary.pdf`

      pdfMake.createPdf(docDefinition).download(summaryFilename)
      setPdfMessage("PDF downloaded!")
      setTimeout(() => setPdfMessage(null), 1500)
    } catch (err) {
      console.error("Error generating PDF:", err)
      setPdfMessage("Failed to generate PDF")
      setTimeout(() => setPdfMessage(null), 2000)
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
    // Executives
    if (overviewBlockData?.executives_list?.length) {
      const execs = overviewBlockData.executives_list
        .map(
          (e) =>
            `* **${e.executive_name || "Not provided"}**: ${
              e.role || "Not provided"
            }`
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
      if (
        overviewBlockData.guidance_outlook &&
        overviewBlockData.guidance_outlook.length
      ) {
        // Group by period_label
        const grouped: Record<
          string,
          { metric_name: string; metric_description: string }[]
        > = {}
        overviewBlockData.guidance_outlook.forEach((item) => {
          const key = item.period_label || "Not provided"
          if (!grouped[key]) grouped[key] = []
          grouped[key].push({
            metric_name: item.metric_name || "Not provided",
            metric_description: item.metric_description || "Not provided",
          })
        })

        const entryTexts: string[] = []
        const htmlEntryParts: string[] = []
        Object.entries(grouped).forEach(([period, items]) => {
          entryTexts.push(`**${period}**`)
          items.forEach((m) => {
            entryTexts.push(`- **${m.metric_name}**: ${m.metric_description}`)
          })
          // blank line between periods
          entryTexts.push("")

          htmlEntryParts.push(
            `<p><strong>${period}</strong></p>` +
              `<ul>` +
              items
                .map(
                  (m) =>
                    `<li><strong>${m.metric_name}</strong>: ${m.metric_description}</li>`
                )
                .join("") +
              `</ul>`
          )
        })

        parts.push(`### Guidance & Outlook\n${entryTexts.join("\n")}`)
        htmlParts.push(
          `<h3>Guidance &amp; Outlook</h3>` + htmlEntryParts.join("")
        )
      }
    }
    // Q&A
    if (resolvedCallType === "earnings" && qaEarnings) {
      const qaText = qaEarnings.analysts
        .map(
          (a) =>
            `**${a.name || "Not provided"} - ${a.firm || "Not provided"}**\n` +
            a.questions
              .map(
                (q) =>
                  `**Q:** ${q.question || "Not provided"}\n**A:** ${
                    q.answer_summary || "Not provided"
                  }`
              )
              .join("\n\n")
        )
        .join("\n\n")
      parts.push(`## Q&A\n${qaText}`)

      htmlParts.push(
        `<h2>Q&amp;A</h2>` +
          qaEarnings.analysts
            .map(
              (a) =>
                `<h3>${a.name || "Not provided"} - ${
                  a.firm || "Not provided"
                }</h3>` +
                `<ul>` +
                a.questions
                  .map(
                    (q) =>
                      `<li><strong style="color: #1a365d;">Q:</strong> <span style="color: #1a365d; font-weight: bold;">${
                        q.question || "Not provided"
                      }</span><br/><strong style="color: #000000;">A:</strong> <span style="color: #000000; ;">${
                        q.answer_summary || "Not provided"
                      }</span></li>`
                  )
                  .join("") +
                `</ul>`
            )
            .join("")
      )
    } else if (resolvedCallType === "conference" && qaConference) {
      const topicText = qaConference.topics
        .map((t) => {
          const pairs = t.question_answers
            .map((analyst) => {
              const qs = analyst.questions
                .map((q: any) => {
                  const qLine = `**Q:** ${q.question || "Not provided"}`
                  if (Array.isArray(q.answers) && q.answers.length > 0) {
                    const blocks = q.answers
                      .map((ans: any) => {
                        const bullets = (ans.answer_summary || [])
                          .map((p: string) => `${p}`)
                          .join("\n")
                        return `**A (${ans.executive})**\n${bullets}`
                      })
                      .join("\n")
                    return `${qLine}\n${blocks}`
                  } else if (Array.isArray(q.answer_summary)) {
                    const bullets = q.answer_summary
                      .map((p: string) => `${p}`)
                      .join("\n")
                    return `${qLine}\n**A:**\n${bullets}`
                  }
                  return `${qLine}\n**A:** ${q.answer_summary || "Not provided"}`
                })
                .join("\n\n")
              return `**${analyst.name || "Not provided"} - ${
                analyst.firm || "Not provided"
              }**\n${qs}`
            })
            .join("\n\n")
          return `### ${t.topic || "Untitled topic"}\n${pairs}`
        })
        .join("\n\n")
      parts.push(`## Q&A\n${topicText}`)

      htmlParts.push(
        `<h2>Q&amp;A</h2>` +
          qaConference.topics
            .map(
              (t) =>
                `<h3>${t.topic || "Untitled topic"}</h3>` +
                `<ul>` +
                t.question_answers
                  .map((analyst) => {
                    const qs = analyst.questions
                      .map((q: any) => {
                        const qHeader = `<strong style=\"color:#1a365d;\">Q:</strong> <span style=\"color:#1a365d;font-weight:bold;\">${
                          q.question || "Not provided"
                        }</span>`
                        if (Array.isArray(q.answers) && q.answers.length > 0) {
                          const groups = q.answers
                            .map(
                              (ans: any) =>
                                `<div><strong>A (${ans.executive})</strong><ul>` +
                                (ans.answer_summary || [])
                                  .map((p: string) => `<li>${p}</li>`)
                                  .join("") +
                                `</ul></div>`
                            )
                            .join("")
                          return `${qHeader}<br/>${groups}`
                        } else if (Array.isArray(q.answer_summary)) {
                          const bullets = q.answer_summary
                            .map((p: string) => `<li>${p}</li>`)
                            .join("")
                          return `${qHeader}<br/><strong>A:</strong><ul>${bullets}</ul>`
                        }
                        return `${qHeader}<br/><strong>A:</strong> <span>${
                          q.answer_summary || "Not provided"
                        }</span>`
                      })
                      .join("<br/>")
                    return `<li><strong>${
                      analyst.name || "Not provided"
                    } - ${analyst.firm || "Not provided"}:</strong><br/>${qs}</li>`
                  })
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

  const handleCopyMetadata = async () => {
    const metadataText = `Q&A Metadata:
Model: ${summaryMeta?.model ?? "Not provided"}
Effort-level: ${summaryMeta?.effort_level ?? "Not provided"}
Duration: ${formatDuration(summaryMeta?.time)}
Input tokens: ${summaryMeta?.input_tokens ?? "Not provided"}
Output tokens: ${summaryMeta?.output_tokens ?? "Not provided"}
${summaryMeta?.reasoning_tokens ? `Reasoning tokens: ${summaryMeta.reasoning_tokens}` : ""}

Overview Metadata:
Model: ${overviewMeta?.model ?? "Not provided"}
Effort-level: ${overviewMeta?.effort_level ?? "Not provided"}
Duration: ${formatDuration(overviewMeta?.time)}
Input tokens: ${overviewMeta?.input_tokens ?? "Not provided"}
Output tokens: ${overviewMeta?.output_tokens ?? "Not provided"}
${overviewMeta?.reasoning_tokens ? `Reasoning tokens: ${overviewMeta.reasoning_tokens}` : ""}

Evaluation Metadata:
${judgeBlocks
  .map(
    ({ metadata }, i) => `
Model: ${metadata?.model ?? "Not provided"}
Effort-level: ${metadata?.effort_level ?? "Not provided"}
Duration: ${formatDuration(metadata?.time)}
Input tokens: ${metadata?.input_tokens ?? "Not provided"}
Output tokens: ${metadata?.output_tokens ?? "Not provided"}`
  )
  .join("\n")}`

    try {
      Clipboard.setString(metadataText)
      setMetaCopied(true)
      setTimeout(() => setMetaCopied(false), 2000)
    } catch (error) {
      console.error("Failed to copy metadata to clipboard:", error)
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

  const parts: string[] = []
  const htmlParts: string[] = []
  const durations: string[] = []
  const tokens: string[] = []

  // Calculate total duration
  const totalSeconds =
    (summaryMeta?.time ?? 0) +
    judgeBlocks.reduce((sum, { metadata }) => sum + (metadata?.time ?? 0), 0) +
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
    )
  }

  parts.push(
    `### Total Duration (${formatDuration(totalSeconds)})\n${durations.join(
      "\n"
    )}`
  )
  parts.push(`### Total Tokens\n${tokens.join("\n\n")}`)

  const plain = parts.join("\n\n")
  const html = `<div>
      <h3>Total Duration (${formatDuration(totalSeconds)})</h3>
      <ul>${htmlDurations.join("")}</ul>
      <h3>Total Tokens</h3>
      <ul>${htmlTokens.join("")}</ul>
    </div>`

  if (!result) {
    return (
      <SafeAreaView style={styles.wrapper}>
        <View style={{ padding: 20 }}>
          <Text style={{ marginBottom: 10 }}>Preparing results...</Text>
          <Text style={{ marginBottom: 4 }}>Stage: {formatStage(stage)}</Text>
          <View style={styles.progressBarOuter}>
            <View
              style={[
                styles.progressBarInner,
                {
                  width: `${Math.max(0, Math.min(100, percentComplete || 0))}%`,
                },
              ]}
            />
          </View>
          <Text style={{ marginTop: 6, color: "#6B7280" }}>
            {Math.round(percentComplete || 0)}%
          </Text>
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
        {/* --- Warning Banner --- */}
        {stages &&
          (stages["overview_summary"] === "failed" ||
            stages["summary_evaluation"] === "failed") && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningText}>
                {stages["overview_summary"] === "failed"
                  ? "Overview unavailable. "
                  : ""}
                {stages["summary_evaluation"] === "failed"
                  ? "Evaluation unavailable."
                  : ""}
              </Text>
            </View>
          )}

        {/* --- Report Block --- */}
        <View style={styles.blockContainer} ref={reportBlockRef}>
          {resolvedCallType === "earnings" ? (
            <EarningsResult
              title={title}
              overview={overviewBlockData}
              qa={qaEarnings}
              onCopyReport={handleCopyReport}
              onSavePdf={handleSavePdf}
              reportCopied={reportCopied}
              pdfMessage={pdfMessage}
              summaryMeta={summaryMeta}
              overviewMeta={overviewMeta}
            />
          ) : (
            <ConferenceResult
              title={title}
              overview={overviewBlockData}
              qaByTopic={qaConference}
              onCopyReport={handleCopyReport}
              onSavePdf={handleSavePdf}
              reportCopied={reportCopied}
              pdfMessage={pdfMessage}
              summaryMeta={summaryMeta}
              overviewMeta={overviewMeta}
            />
          )}
        </View>

        <View style={styles.divider} />

        {/* --- Judge Evaluation Block --- */}
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

          {/* Show loading state if judge evaluation is still processing or not available yet */}
          {(stages && stages["summary_evaluation"] === "processing") ||
            ((!judgeBlocks || judgeBlocks.length === 0) &&
              (!stages || stages["summary_evaluation"] !== "failed") && (
                <View style={styles.loadingContainer}>
                  <Animated.View
                    style={[
                      styles.loadingSpinner,
                      { transform: [{ rotate: spin }] },
                    ]}
                  >
                    <Ionicons name="refresh" size={24} color="#007AFF" />
                  </Animated.View>
                  <Text style={styles.loadingText}>Loading evaluation...</Text>
                </View>
              ))}

          {/* Show judge evaluation when available */}
          {judgeBlocks && judgeBlocks.length > 0 && (
            <JudgeEvaluation judgeBlocks={judgeBlocks} />
          )}

          {/* Show error state if judge evaluation failed */}
          {stages && stages["summary_evaluation"] === "failed" && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>Evaluation unavailable</Text>
            </View>
          )}
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
              <TouchableOpacity
                onPress={handleCopyMetadata}
                style={{ marginRight: 8 }}
              >
                <Ionicons name="copy-outline" size={30} color="#007AFF" />
              </TouchableOpacity>
              <Ionicons
                name={
                  isMetadataVisible
                    ? "chevron-up-outline"
                    : "chevron-down-outline"
                }
                size={30}
                color="#3C3C43"
              />
            </View>
          </TouchableOpacity>

          {isMetadataVisible && (
            <View style={{ marginTop: 10 }}>
              {/* Q&A Metadata */}
              <Text style={styles.h3}>Q&A Metadata</Text>
              <View style={styles.metadataSection}>
                <Text style={styles.metadataDetail}>
                  Model: {summaryMeta?.model ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Effort-level: {summaryMeta?.effort_level ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Duration: {formatDuration(summaryMeta?.time)}
                </Text>
                <Text style={styles.metadataDetail}>
                  Input tokens: {summaryMeta?.input_tokens ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Output tokens: {summaryMeta?.output_tokens ?? "Not provided"}
                </Text>
                {summaryMeta?.reasoning_tokens && (
                  <Text style={styles.metadataDetail}>
                    Reasoning tokens: {summaryMeta.reasoning_tokens}
                  </Text>
                )}
              </View>

              {/* Overview Metadata */}
              <Text style={styles.h3}>Overview Metadata</Text>
              <View style={styles.metadataSection}>
                <Text style={styles.metadataDetail}>
                  Model: {overviewMeta?.model ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Effort-level: {overviewMeta?.effort_level ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Duration: {formatDuration(overviewMeta?.time)}
                </Text>
                <Text style={styles.metadataDetail}>
                  Input tokens: {overviewMeta?.input_tokens ?? "Not provided"}
                </Text>
                <Text style={styles.metadataDetail}>
                  Output tokens: {overviewMeta?.output_tokens ?? "Not provided"}
                </Text>
                {overviewMeta?.reasoning_tokens && (
                  <Text style={styles.metadataDetail}>
                    Reasoning tokens: {overviewMeta.reasoning_tokens}
                  </Text>
                )}
              </View>

              {/* Evaluation Metadata */}
              <Text style={styles.h3}>Evaluation Metadata</Text>
              {(stages && stages["summary_evaluation"] === "processing") ||
              ((!judgeBlocks || judgeBlocks.length === 0) &&
                (!stages || stages["summary_evaluation"] !== "failed")) ? (
                <View style={styles.metadataSection}>
                  <View style={[styles.loadingContainer, { padding: 10 }]}>
                    <Animated.View
                      style={[
                        styles.loadingSpinner,
                        { transform: [{ rotate: spin }] },
                      ]}
                    >
                      <Ionicons name="refresh" size={20} color="#007AFF" />
                    </Animated.View>
                    <Text style={[styles.loadingText, { fontSize: 14 }]}>
                      Loading evaluation metadata...
                    </Text>
                  </View>
                </View>
              ) : stages && stages["summary_evaluation"] === "failed" ? (
                <View style={styles.metadataSection}>
                  <Text style={styles.metadataDetail}>
                    Evaluation unavailable
                  </Text>
                </View>
              ) : (
                judgeBlocks.map(({ metadata }, i) => (
                  <View key={i} style={styles.metadataSection}>
                    <Text style={styles.metadataDetail}>
                      Model: {metadata?.model ?? "Not provided"}
                    </Text>
                    <Text style={styles.metadataDetail}>
                      Effort-level: {metadata?.effort_level ?? "Not provided"}
                    </Text>
                    <Text style={styles.metadataDetail}>
                      Duration: {formatDuration(metadata?.time)}
                    </Text>
                    <Text style={styles.metadataDetail}>
                      Input tokens: {metadata?.input_tokens ?? "Not provided"}
                    </Text>
                    <Text style={styles.metadataDetail}>
                      Output tokens: {metadata?.output_tokens ?? "Not provided"}
                    </Text>
                  </View>
                ))
              )}
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
  boldText: { fontWeight: "bold", fontSize: 14, paddingBottom: 3 },
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
  progressBarOuter: {
    height: 10,
    width: "100%",
    backgroundColor: "#EEE",
    borderRadius: 6,
    overflow: "hidden",
    marginTop: 4,
  },
  progressBarInner: {
    height: 10,
    backgroundColor: "#007AFF",
  },
  warningBanner: {
    backgroundColor: "#FFF8E1",
    borderColor: "#F59E0B",
    borderWidth: 1,
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
  },
  warningText: {
    color: "#92400E",
    fontSize: 14,
  },
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
  loadingContainer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  loadingSpinner: {
    marginRight: 10,
  },
  loadingText: {
    fontSize: 16,
    color: "#666",
  },
  errorContainer: {
    padding: 20,
    alignItems: "center",
  },
  errorText: {
    fontSize: 16,
    color: "#FF3B30",
  },
})

function formatStage(s?: string | null): string {
  if (!s) return "Starting..."
  const pretty = s.replace(/_/g, " ")
  return pretty.charAt(0).toUpperCase() + pretty.slice(1)
}
