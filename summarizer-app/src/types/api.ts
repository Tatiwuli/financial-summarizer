// API Response Types
export interface ValidationResponse {
  is_validated: boolean
  validated_at?: string
  input?: {
    call_type?: string
    summary_length?: string
    filename?: string
  }
  transcript_name?: string
  filename?: string
  job_id: string
}

export interface SummaryResponse {
  job_id: string
  transcript_name: string
  current_stage:
    | "q_a_summary"
    | "overview_summary"
    | "summary_evaluation"
    | "completed"
    | "failed"
  stages: Record<string, "pending" | "running" | "completed" | "failed">
  percent_complete: number
  updated_at: string
  input?: {
    call_type?: string
    summary_length?: string
    filename?: string
  }
  outputs?: {
    q_a_summary?: any // Will be properly typed when we have the specific types
    overview_summary?: any
    summary_evaluation?: any
  }
  error?: {
    code?: string
    message?: string
  }
}

export interface CancelJobResponse {
  ok: boolean
  job_id: string
  status: string
}

export interface PromptVersionsResponse {
  earnings: {
    long: {
      q_a: string[]
      overview: string[]
      judge: string[]
    }
    short: {
      q_a: string[]
      overview: string[]
      judge: string[]
    }
  }
  conference: {
    long: {
      q_a: string[]
      overview: string[]
      judge: string[]
    }
    short: {
      q_a: string[]
      overview: string[]
      judge: string[]
    }
  }
}
