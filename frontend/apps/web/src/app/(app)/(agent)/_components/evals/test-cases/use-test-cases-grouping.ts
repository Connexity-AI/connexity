'use client';

import { useMemo, useState } from 'react';

import type { TestCasesTagGroup } from '@/app/(app)/(agent)/_components/evals/test-cases/grouped-test-cases-table';
import type { TestCasePublic } from '@/client/types.gen';

export function useTestCasesGrouping(filtered: TestCasePublic[]) {
  const [groupByTags, setGroupByTags] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const toggle = () => setGroupByTags((value) => !value);

  const toggleGroup = (tag: string) => {
    setCollapsedGroups((previous) => {
      const next = new Set(previous);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  };

  const tagGroups = useMemo<TestCasesTagGroup[]>(() => {
    const sortedTags = Array.from(new Set(filtered.flatMap((item) => item.tags ?? []))).sort();

    const tagged: TestCasesTagGroup[] = sortedTags
      .map((tag) => ({
        tag,
        items: filtered.filter((item) => (item.tags ?? []).includes(tag)),
      }))
      .filter((group) => group.items.length > 0);

    const untagged = filtered.filter((item) => (item.tags ?? []).length === 0);
    if (untagged.length > 0) {
      tagged.push({ tag: '__untagged__', items: untagged });
    }

    return tagged;
  }, [filtered]);

  return {
    groupByTags,
    toggle,
    collapsedGroups,
    toggleGroup,
    tagGroups,
  };
}
