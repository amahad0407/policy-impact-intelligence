export type SourceType = 'official' | 'opinion' | 'reporting' | 'ai';
export type ImpactType = 'positive' | 'negative' | 'mixed' | 'neutral';
export type ConfidenceLevel = 'high' | 'medium' | 'low';
export type PolicyStatus = 'Active' | 'Struck Down' | 'Under Review' | 'Removed';

export interface Evidence {
  id: string;
  excerpt: string;
  sourceType: SourceType;
  sourceDocument: string;
  sourceUrl?: string;
}

export interface Finding {
  id: string;
  claim: string;
  sourceType: SourceType;
  confidence: ConfidenceLevel;
  evidence: Evidence[];
}

export interface Stakeholder {
  id: string;
  name: string;
  description: string;
  impact: ImpactType;
  scale: string;
  affectedCount?: string;
}

export interface PolicyDoc {
  title: string;
  subtitle: string;
  agency: string;
  docketId: string;
  documentType: string;
  publishedDate: string;
  status: PolicyStatus;
  pageCount: number;
}

export interface StatCardData {
  label: string;
  value: string;
  description: string;
}
