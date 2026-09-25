// Raw types matching the shape of data/processed/policy_summary.json
// (snake_case from the Python backend)

export interface ApiEvidence {
  excerpt: string;
  source_document: string;
  source_section: string;
}

export interface ApiFinding {
  claim: string;
  source_type: 'official' | 'opinion' | 'reporting' | 'ai';
  confidence: 'high' | 'medium' | 'low';
  evidence: ApiEvidence[];
}

export interface ApiStakeholder {
  group: string;
  description: string;
  impact: 'positive' | 'negative' | 'mixed' | 'neutral';
  evidence_excerpt: string;
  source_document: string;
  source_section: string;
}

export interface ApiDefinition {
  term: string;
  definition: string;
  source_document: string;
  source_section: string;
}

export interface ApiSourceDocument {
  label: string;
  document_number: string;
  title: string;
  publication_date: string;
  source_url: string;
}

export interface ApiMetadata {
  generated_at: string;
  deployment: string;
  input_tokens: number;
  output_tokens: number;
  source_documents: ApiSourceDocument[];
}

export interface PolicyAnalysis {
  policy_summary: string;
  key_changes: string[];
  affected_stakeholders: ApiStakeholder[];
  important_definitions: ApiDefinition[];
  findings: ApiFinding[];
  uncertainty_or_limitations: string[];
  _metadata: ApiMetadata;
}

// ── Comments Analysis (from data/processed/comments_analysis.json) ──────────

export interface CommentEvidence {
  comment_id: string;
  excerpt: string;
  source_url: string;
}

export interface CommentTheme {
  theme: string;
  description: string;
  comment_count: number;
  evidence: CommentEvidence[];
}

export interface CommentViewpoint {
  label: string;
  description: string;
  comment_count: number;
  evidence: CommentEvidence[];
}

export interface CommentsMetadata {
  generated_at: string;
  deployment: string;
  sample_size: number;
  total_comments_in_docket: number | string;
  sample_note: string;
  input_tokens: number;
  output_tokens: number;
}

export interface CommentsAnalysis {
  summary: string;
  themes: CommentTheme[];
  viewpoints: CommentViewpoint[];
  affected_groups: string[];
  limitations: string[];
  _metadata: CommentsMetadata;
}

// ── News Analysis (from data/processed/news_analysis.json) ───────────────────

export interface NewsArticle {
  headline: string;
  publication: string;
  date: string;
  url: string;
  source_type: 'reporting' | 'analysis' | 'opinion';
  summary: string;
  policy_issue: string;
}

export interface NewsMetadata {
  generated_at: string;
  deployment: string;
  articles_analyzed: number;
  input_tokens: number;
  output_tokens: number;
  source_note: string;
}

export interface NewsAnalysis {
  summary: string;
  articles: NewsArticle[];
  key_developments: string[];
  coverage_themes: string[];
  limitations: string[];
  _metadata: NewsMetadata;
}

// ── Briefing Analysis (from data/processed/briefing_analysis.json) ───────────

export interface BriefingViewpoint {
  label: string;
  description: string;
  source: string;
}

export interface BriefingPublicFeedback {
  summary: string;
  themes: string[];
  viewpoints: BriefingViewpoint[];
}

export interface BriefingNewsCoverage {
  summary: string;
  developments: string[];
}

export interface BriefingStakeholder {
  group: string;
  impact: string;
  description: string;
  sources: string[];
}

export interface BriefingSource {
  label: string;
  type: 'official' | 'public_comment' | 'news';
  description: string;
  url: string;
}

export interface BriefingMetadata {
  generated_at: string;
  deployment: string;
  input_tokens: number;
  output_tokens: number;
  sources_used: string[];
  disclaimer: string;
}

export interface BriefingAnalysis {
  executive_summary: string;
  policy_context: string;
  key_policy_changes: string[];
  public_feedback: BriefingPublicFeedback;
  news_coverage: BriefingNewsCoverage;
  stakeholders: BriefingStakeholder[];
  areas_of_alignment: string[];
  areas_of_difference: string[];
  uncertainties_and_limitations: string[];
  sources: BriefingSource[];
  _metadata: BriefingMetadata;
}

// ── Comparison Analysis (from data/processed/comparison_analysis.json) ───────

export interface ComparisonChange {
  topic: string;
  proposed: string;
  final: string;
  change_description: string;
}

export interface ComparisonDefinition {
  term: string;
  proposed_definition: string;
  final_definition: string;
  changed: boolean;
}

export interface ComparisonTimelineEvent {
  date: string;
  event: string;
  document: string;
}

export interface ComparisonSource {
  label: string;
  document_number: string;
  publication_date: string;
  url: string;
}

export interface ComparisonMetadata {
  generated_at: string;
  deployment: string;
  input_tokens: number;
  output_tokens: number;
  proposed_doc: string;
  final_doc: string;
  disclaimer: string;
}

export interface ComparisonAnalysis {
  summary: string;
  key_changes: ComparisonChange[];
  unchanged_elements: string[];
  definitions: ComparisonDefinition[];
  timeline: ComparisonTimelineEvent[];
  limitations: string[];
  sources: ComparisonSource[];
  _metadata: ComparisonMetadata;
}
