import type { StatCardData, PolicyDoc } from '@/types';

export const currentPolicy: PolicyDoc = {
  title: 'Non-Compete Clause Rule',
  subtitle: 'Banning Non-Compete Agreements Across the U.S. Economy',
  agency: 'Federal Trade Commission',
  docketId: 'FTC-2023-0007',
  documentType: 'Final Rule',
  publishedDate: 'May 7, 2024',
  status: 'Struck Down',
  pageCount: 570,
};

export const statsData: StatCardData[] = [
  {
    label: 'Policy Documents',
    value: '2',
    description: 'Proposed (Jan 2023) + Final Rule (May 2024)',
  },
  {
    label: 'Identified Stakeholder Groups',
    value: '4',
    description: 'Workers, employers, trade groups, and more',
  },
  {
    label: 'Public Comments',
    value: '20,697',
    description: 'Submitted to docket FTC-2023-0007',
  },
  {
    label: 'Source Types',
    value: '3',
    description: 'Official documents · Public feedback · News',
  },
];
