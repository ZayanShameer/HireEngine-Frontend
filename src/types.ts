// Hirengine AI Shared Types Spec

export type TargetDomain = 
  | 'Oil & Gas' 
  | 'Petrochemical' 
  | 'Construction & Infrastructure' 
  | 'Energy'
  | 'Hospitality'
  | 'Healthcare'
  | 'Facilities Management'
  | 'Maritime & Shipping' 
  | 'Power Plants' 
  | 'Engineering Services'
  | 'Manufacturing'
  | 'EPC';

export type HiringStage = 
  | 'Screening' 
  | 'Shortlist' 
  | 'Interviewing' 
  | 'Offered' 
  | 'Hired' 
  | 'Rejected';

export interface Requisition {
  id: number;
  job_title: string;
  location: string;
  target_domain: TargetDomain;
  job_description_text: string;
  created_at: string; // ISO Timestamp
}

export interface Candidate {
  id: number;
  requisition_id: number;
  full_name: string;
  email: string;
  phone: string;
  passport_number: string | null;
  current_stage: HiringStage;
  total_experience_years: number;
  relevant_experience_years: number;
  match_score: number; // 0 to 100
  skills_matrix: string[]; // GIN indexed skills array
  specialization_tags: string[]; // GIN indexed tags (e.g. ['13.8KV', '380KV'])
  industry_remarks: string; // Context-aware validation summary
  cv_file_name?: string; // Stored filename on backend (e.g. 'a3f9b2c1_John_CV.pdf')
  ai_analysis?: {
    summary?: string;
    strengths?: string[];
    gaps?: string[];
    interview_questions?: string[];
  };
  eligible?: boolean;
  veto_reason?: string | null;
  created_at: string; // ISO Timestamp
}

// Queue Item state interface for Parallel Ingestion Engine
export interface QueueItem {
  id: string;
  fileName: string;
  fileSize: number;
  progress: number; // 0 to 100
  status: 'pending' | 'extracting' | 'scoring' | 'completed' | 'failed';
  error?: string;
  parsedData?: Partial<Candidate>;
  file?: File;
}

// State management search filters for Faceted Search Sidebar
export interface FilterState {
  searchQuery: string;
  domains: TargetDomain[];
  specializationTags: string[];
  minExperience: number;
  matchScoreRange: [number, number]; // [min, max]
  stages: HiringStage[];
}

export interface CandidateNote {
  id: number;
  candidate_id: number;
  author_email: string;
  note_text: string;
  created_at: string;
}
