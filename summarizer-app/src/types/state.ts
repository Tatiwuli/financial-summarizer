// State Management Types

export type SummaryStatus =
  | "idle"
  | "validating"
  | "validated"
  | "loading"
  | "success"
  | "error"

export interface ValidationState {
  isValidated: boolean
  filename?: string
  validatedAt?: string
}

export interface SummaryState {
  status: SummaryStatus
  error: string | null
  messageType?: "error" | "success" | "info" // Add message type for styling
  isWaitingForServer?: boolean // Track if user is waiting for server reconnection
  result: any | null // Will be properly typed when we import SummaryResult
  validation: ValidationState | null
  jobId?: string | null
  transcriptName?: string | null
  stage?: string | null
  percentComplete?: number | null
  warnings?: string[]
  stages?: Record<string, string> | null
  currentCallType?: "earnings" | "conference"
  cancel: () => Promise<void>
  summarize: (
    file: File | any, // DocumentPickerAsset from expo-document-picker
    callType: string,
    summaryLength: string,
    promptVersions?: {
      q_a?: "prose" | "bullet"
      overview?: string
      judge?: string
    }
  ) => Promise<void>
  reset: () => void
}

// Prompt Version Types
export interface PromptVersionConfig {
  q_a?: string
  overview?: string
  judge?: string
}

export interface AvailablePromptVersions {
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
