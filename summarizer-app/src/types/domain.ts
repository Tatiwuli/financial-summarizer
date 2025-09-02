// Domain/Business Logic Types

// Defines the structure for a single Q&A item
export interface AnswerByExecutiveBullet {
  executive: string
  answer_summary: string[]
}

export interface Question {
  question: string
  // legacy prose or flat bullets
  answer_summary?: string | string[]
  // new grouped bullets by executive
  answers?: AnswerByExecutiveBullet[]
}

// Defines the structure for an analyst and their questions
export interface AnalystQA {
  name: string
  firm: string
  questions: Question[]
}

// Defines the shape of the data inside a 'q_a' block
export interface QABlock {
  title: string
  analysts: AnalystQA[]
}

export interface Topic {
  topic: string
  question_answers: AnalystQA[]
}

export interface QABlockByTopic {
  title: string
  topics: Topic[]
}

// Defines the shape of the data inside an 'overview' block
export interface OverviewBlockData {
  executives_list: Array<{ executive_name: string; role: string }>
  overview: string
  guidance_outlook?: Array<{
    period_label: string
    metric_name: string
    metric_description: string
  }>
 
}

// Defines the shape of the data inside a 'judge' block
export interface JudgeBlockData {
  evaluation_results: Array<{
    metric_name: string
    passed: boolean
    errors: Array<{
      error: string
      summary_text: string
      transcript_text: string
    }>
  }>
  overall_assessment: {
    total_criteria: number
    passed_criteria: number
    failed_criteria: number
    overall_passed: boolean
    pass_rate: number
    evaluation_timestamp: string
    evaluation_summary: string
  }
}

// The main result object
export interface SummaryResult {
  title: string
  call_type: string
  blocks: Array<{
    type: "overview" | "q_a_short" | "q_a_long" | "judge"
    data: QABlock | QABlockByTopic | OverviewBlockData | JudgeBlockData
    metadata?: SummaryMetadata | JudgeMetadata | OverviewMetadata
  }>
}

// Metadata types
export interface SummaryMetadata {
  model: string
  summary_length: string
  prompt_version: string
  summary_structure: string
  call_type: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  raw_response?: unknown
}

export interface JudgeMetadata {
  model: string
  prompt_version: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  raw_response?: unknown
}

export interface OverviewMetadata {
  model: string
  prompt_version: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  raw_response?: unknown
}
