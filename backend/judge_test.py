# from src.services.summary_workflow import run_judge_workflow
# from src.services.precheck import run_validate_file
# import os
# import json
# from fastapi import UploadFile
# from src.utils.pdf_processor import create_pdf_processor, PDFProcessingError
# from src.config.runtime import save_transcripts_dir, CALL_TYPE

# q_a_summary = """
# Atlassian Corporation, Q4 2025 Earnings Call, Aug 07, 2025
# Analyst: Keith Weiss, Morgan Stanley
# Question 1: Congrats on the strong end to the year. The market is concerned that code-generation tools will negatively impact developers, but you seem to view it as a positive. What are you seeing in the business today regarding seat expansion, and how will these AI innovations affect Atlassian's core business going forward?
# Answer Summary: The company is seeing no negative impact on its numbers, including expansion, growth, or adoption rates for its technical products. Customer usage of Atlassian products does not change when they integrate code-generating AI tools, and user growth remains healthy. Early data indicates that Jira instances connected to cogeneration tools show faster business user growth than those without, reinforcing Jira's role as a work hub.
# Management believes there will be far more, not fewer, developers in five years, and the cost of building software will go down, which significantly expands Atlassian's opportunity. Internally, Atlassian uses its own Rovo Dev (built on SWE-bench) and 3-4 other cogeneration tools with over 1,000 users each, which has led to creating more and better software while still hiring engineers. The company views AI as a "huge tailwind" for its business, which is focused on solving collaboration and people problems.
# Analyst: Alex Mulan, Jefferies
# Question 1: Free cash flow was broadly flat this year at around $1.5 billion. How should we think about the FCF trajectory for 2026?
# Answer Summary: Q4 free cash flow was $360 million, down 13% year-over-year, which was expected and primarily driven by strong collections in the prior year related to the server end-of-support dynamics. There are short-term headwinds from transitioning multiyear agreements to annual billing (from upfront) and more back-loaded sales from the growing enterprise cloud business.
# Guidance: Over time, free cash flow is expected to correlate with non-GAAP operating income trends. Management expects about a 500 basis point difference between non-GAAP operating margin and free cash flow margin for FY '26 and beyond, though this may vary quarter-to-quarter due to timing differences like the Q1 employee bonus payout.
# Analyst: Kash Rangan, Goldman Sachs
# Question 1: Acknowledging that AI is not reducing developer jobs, the numbers imply an acceleration is needed in FY '27 to meet long-term growth guidance. What are the potential inflection points or levers (GTM, enterprise, migrations) to achieve that acceleration?
# Answer Summary: (Joe Binz) The FY '26 guidance uses a "conservative and risk-adjusted approach," similar to FY '25, to account for macro uncertainty and potential disruption from the evolving enterprise go-to-market motion. Management reaffirmed its confidence in delivering 20% compounded annual growth from FY '24 through FY '27, stating that 20% growth in FY '25 laid a strong foundation. Growth levers include paid seat expansion, cross-sell, upsell, pricing, new customer growth, and opportunities from AI.
# (Mike Cannon-Brookes) Management is "incredibly confident" in the long-term revenue and margin targets. The new Teamwork Collection had a "very strong" first three months and is at the apex of the company's three transformations (Enterprise, AI, System of Work).
# Customer examples validating this include:
# A "world's largest automotive manufacturer" purchased Teamwork Collection for "high tens of thousands of users," citing integrated AI as a core reason.
# One of the "world's leading chip companies" migrated "tens of thousands of users" from Data Center to Cloud, specifically mentioning AI capabilities like Rovo search and Rovo chat as large-scale reasons for the move.
# Analyst: Michael Turrin, Wells Fargo
# Question 1: Congrats on the year-end. Can you expand on the framework for the FY '26 guide, particularly the "Enterprise go-to-market" risk? How did FY '25 close relative to the embedded execution risk, and how does that compare to the initial guide for '26?
# Answer Summary: The company saw "great execution" from its sales team and partners in Q4, driving strong bookings and billings. This included a record number of deals over $1 million, Data Center to Cloud migrations being up 60% year-over-year, and strong momentum for the new Teamwork Collection. This performance led to Remaining Performance Obligations (RPO) increasing to $3.3 billion (up 38% YoY), with 74% of that balance to be recognized as revenue in the next 12 months (up 29% YoY).
# The initial FY '25 guidance had assumed a negative impact on paid seat expansion and cloud migrations from macro uncertainty and the GTM evolution, but "neither one of those were fully materialized." The primary drivers of the Q4 cloud revenue outperformance were paid seat expansion (which showed quarter-to-quarter stability in SMB and enterprise), cross-sell, and migrations.
# Analyst: Arsenije Matovic, Wolfe Research
# Question 1: Given the strong early traction with Teamwork Collection, can we expect more AI capabilities or feature launches within the collection this year to drive that momentum?
# Answer Summary: New capabilities will "absolutely" be shipped in the year ahead, and management stated, "you can probably take that one to the bank." AI is viewed as "one of the best things that ever happened to Atlassian." Momentum is demonstrated by the 120% net expansion rate and growth in monthly AI users from 1.5 million last quarter to 2.3 million this quarter. Token usage is up 5x quarter-on-quarter. Recent launches include the Rovo Dev CLI, and the company is working with Anthropic on MCP servers (in beta) and with OpenAI on GPT-5. An example of AI's impact is in Confluence, where users who use the editor AI create 15% more pages and make 33% more edits.
# Question 2: Can you help us understand the "mid-single-digit" migration contribution in the FY '26 Cloud guidance? How did migration growth contribute in FY '25, and what is driving the conservatism for FY '26?
# Answer Summary: In FY '25, migrations contributed in the "mid- to high single-digit range" to cloud revenue growth. This was driven by investments in customer success programs like Fast shift and R&D that adds value to the cloud platform.
# Guidance: The FY '26 guidance assumes a sequentially lower contribution from migrations, in the "mid- to single-digit range." This conservatism is due to: 1) the remaining Data Center customers being the largest and most complex to migrate, 2) many migrating via a hybrid approach over time, and 3) the general macro and GTM evolution risks embedded in the overall guidance.
# Outlook: Longer-term, over the next 2-3 years, migrations are still expected to contribute in the "mid- to high single-digit" range to Cloud revenue growth.
# Analyst: Arjun Bhatia, William Blair
# Question 1: With strong Q4 enterprise results, how are you thinking about go-to-market changes to continue enterprise acceleration in 2026? Is this a one-year effort or a multiyear journey into FY '27?
# Answer Summary: This is a multi-year journey to improve what is already a "really great enterprise business" with hundreds of customers paying over $1 million in run rate. There is a $14 billion addressable market opportunity within the existing customer base alone, and while over 80% of the Fortune 500 are customers, they represent only about 10% of the business.
# The enterprise transformation is an ongoing effort. Key areas of continuous improvement under the new sales leadership include:
# Becoming more customer-centric and building deeper partnerships.
# Improving customer success operations from "good to great."
# Enhancing sales operations and systems to handle increased scale and deal velocity.
# Strengthening the partner ecosystem, including bringing more GSIs on board.
# Improving the sales culture.
# Analyst: Karl Keirstead, UBS
# Question 1: The Q1 guide for Data Center growth is a large step-down. Can you unpack that? Is there anything unique about the September quarter causing caution?
# Answer Summary: The Q1 Data Center guidance is approximately 8%. The step-down from Q4 is primarily because Q1 is a seasonally weaker quarter with a "much bigger expiration base in Q4 than we do have in Q1," offering less opportunity for expansion and price increases. Additional factors include headwinds from a programmatic change to 1-year deal terms made a year ago and the company beginning to lap the benefits from the server end-of-support migrations.
# Analyst: Gregg Moskowitz, Mizuho
# Question 1: How do you convince Global 2000 organizations to go "wall-to-wall" and equip every non-technical professional (sales, finance, HR, etc.) with a license, given penetration is much lower there than with technical teams?
# Answer Summary: The company is already seeing significant momentum in consolidation, which has become a "real weapon," and growth in the business user segment is accelerating. Key drivers for non-technical adoption include:
# Product Packaging: The Teamwork Collection separates software tools from broader collaboration tools, making it more accessible.
# Usability: Investments in design, speed, and performance are improving products like Jira for business teams.
# Portfolio Breadth: Loom is very successful in sales teams, and Trello has long been popular with non-technical users.
# AI and Rovo: Rovo search connectors and Rovo agents can run across business workflows in sales and marketing, connecting data from third-party tools.
# Importantly, the technology team usage continues to grow simultaneously; it is not one at the expense of the other.
# Analyst: David E. Hynes, Canaccord Genuity Corp.
# Question 1: How should we think about the bridge from Rovo MAU growth to monetization? What's the timeline, and will it manifest first in consumption, usage, or more effective cross-sell?
# Answer Summary: (Joe Binz) The primary focus for Rovo is on deployment, usage, and engagement, with monetization being a "secondary, longer-term" consideration. While the FY '26 plan includes some consumption-based revenue from Rovo, the guidance assumes "very nominal amounts." The company expects broader benefits to materialize over time, such as seat expansion and upgrades to higher editions.
# (Mike Cannon-Brookes) Monetization is already occurring through multiple vectors:
# Teamwork Collection: The uplift from this bundle is partly AI-driven, and it includes a much larger set of AI credits to encourage usage.
# Edition Upgrades: Premium and Enterprise edition core offerings grew ~40% year-on-year, driven in part by AI value.
# Consumption Models: The company is deploying consumption pricing in areas like Forge, Bitbucket pipelines, Jira Service Management virtual agents, and AI credits.
# Future SKUs: There is a SKU for non-Atlassian users to access Rovo search and chat, which is a potential medium-term growth vector.
# The focus remains on usage first, as evidenced by 5x quarter-on-quarter token usage growth.
# Analyst: Jason Vincent Celino, KeyBanc Capital Markets
# Question 1: The FY '26 operating margin guidance of 24% is close to the FY '27 target of over 25%. What are the key investment priorities this year, such as expanding the sales count for the service management side?
# Answer Summary: (Joe Binz) The company expects to maintain "largely consistent growth rates" for operating expenses from FY '25 to FY '26. The primary investments will be in S&M and R&D, focused on Enterprise Cloud, AI, and the System of Work strategy.
# Guidance: The 24% operating margin guide for FY '26 is based on a conservative revenue forecast. Gross margins are expected to be "relatively stable" as cloud infrastructure optimization offsets higher cloud mix and increased AI usage costs. Management is "confident" in achieving the FY '27 non-GAAP operating target of "in excess of 25%." The company will manage costs carefully, at times reinvesting revenue outperformance and at other times letting it drop to the bottom line to meet profitability commitments.
# (Mike Cannon-Brookes) The company was ahead of target for sales hiring in Q4, which is seen as a positive investment in the enterprise opportunity. He reiterated that the 25% margin target for FY '27 is "very important" and that the company is balancing heavy investment in AI while ensuring it meets its targets, as it did in FY '25.


# """
# summary_structure_json = """ "title": "[Company name] [Quarter, date if available]",
#         "analysts": [
#           {
#             "name": "[Analyst Name]",
#             "firm": "[Firm]",
#             "questions": [
#               {
#                 "question": "[ Question text, preserving relevant sentiment and context and removing filler words]",
#                 "answer_summary": "[Concise, factual summary including exact metrics, context, products, tools, business drivers, forward-looking metrics, and sentiment]"
#               }
#             ]
#             """
# summary_structure_text = """
# #Title
# **Analyst Name (Firm)**
# **Question**:
# **Answer Summary**:

# """

# file_path = r"C:\Users\innyw\OneDrive - minerva.edu\kapitalo\Atlassian Corporation, Q4 2025 Earnings Call, Aug 07, 2025 – Atlassian Corporation – BamSEC.pdf"


# def pdf_path_check(file_path):
#     processor = create_pdf_processor(save_transcripts_dir=save_transcripts_dir)

#     result = processor.process_pdf(file_path)

#     # DEBUG: Log all keys in the result
#     print(f"[DEBUG PRECHECK] Result keys: {list(result.keys())}")
#     print(f"[DEBUG PRECHECK] Full result: {result}")

#     # DEBUG: Log the extracted content lengths and snippets
#     pres_transcript = result.get("presentation_transcript", "")
#     # Fixed: use correct key with underscore
#     qa_transcript = result.get("q_a_transcript", "")

#     print(f"[DEBUG PRECHECK] Presentation length: {len(pres_transcript)}")
#     print(f"[DEBUG PRECHECK] Q&A length: {len(qa_transcript)}")
#     print(f"[DEBUG PRECHECK] Q&A transcript exists: {bool(qa_transcript)}")

#     if pres_transcript:
#         print(
#             f"[DEBUG PRECHECK] Presentation preview (first 200 chars): {pres_transcript[:200]}...")

#     if qa_transcript:
#         print(
#             f"[DEBUG PRECHECK] Q&A preview (first 200 chars): {qa_transcript[:200]}...")
#     else:
#         print("[DEBUG PRECHECK] Q&A transcript is empty or None!")

#     pres_len = result.get("presentation_text_length")
#     qa_len = result.get("qa_text_length")

#     envelope = {
#         "title": result.get("original_filename") or "Documento",

#         "blocks": [
#             {
#                 "type": "precheck",
#                 "data": {
#                     # Fixed: use correct key
#                     "qa_transcript": result.get("q_a_transcript"),
#                     "presentation_transcript": result.get("presentation_transcript"),
#                     "pdf": {
#                         "original_filename": result.get("original_filename"),
#                         "uuid_filename": result.get("uuid_filename"),
#                         "transcript_path": result.get("transcript_path"),
#                         "presentation_text_length": pres_len,
#                         "qa_text_length": qa_len
#                     }
#                 }
#             }
#         ],
#         "meta": {
#             "generated_at": None
#         }
#     }

#     return envelope


# # Extract QA transcript from precheck blocks
# precheck_result = pdf_path_check(file_path)
# blocks = precheck_result.get("blocks", [])
# data = blocks[0].get("data", {}) if blocks else {}
# qa_transcript = data.get("qa_transcript")


# version_prompt = "version_2"

# print("Generated by  me")
# run_judge_workflow(version_prompt=version_prompt, qa_transcript=qa_transcript,
#                    qa_summary=q_a_summary, summary_structure=summary_structure_text)


# version_prompt = "version_3"
# run_judge_workflow(version_prompt=version_prompt, qa_transcript=qa_transcript,
#                    qa_summary=q_a_summary, summary_structure=summary_structure_text)
