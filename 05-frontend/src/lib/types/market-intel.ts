export type RiskLevel = 'low' | 'medium' | 'high';
export type PostStatus = 'draft' | 'pending_review' | 'approved' | 'rejected' | 'expired' | 'published';

export interface AIGeneratedPost {
  id: string;
  title: string;
  content: string;
  recommendation: string | null;
  vertical: string | null; // e.g. "Gambling В· EU"
  priority_score: number | null;
  risk_level: RiskLevel | null;
  status: PostStatus;
  
  // Feature flags for auto modes
  pattern_id: string | null; // Indicates Stage 4 auto-parsing
  
  moderated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImpactBrief {
  id: string;
  compunknown_id: string;
  source_post_id: string | null;
  title: string;
  content: string;
  recommendation: string | null;
  generated_at: string;
}

