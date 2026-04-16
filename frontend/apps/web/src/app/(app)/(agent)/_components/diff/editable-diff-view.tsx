'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import dynamic from 'next/dynamic';

import { Check, Loader2 } from 'lucide-react';
import { useTheme } from 'next-themes';

import { cn } from '@workspace/ui/lib/utils';

import { useDraftAutosave } from '@/app/(app)/(agent)/_hooks/use-draft-autosave';

import type {
  DiffBeforeMount,
  DiffOnMount,
  MonacoDiffEditor,
} from '@monaco-editor/react';

interface EditableDiffViewProps {
  fromContent: string;
  toContent: string;
  editable: boolean;
  agentId: string;
  // When provided, the component runs in *controlled* mode: every modified-
  // side edit is handed up to the parent and the internal draft autosave is
  // bypassed entirely. Used by the AI suggestion flow, where edits commit on
  // explicit Accept rather than per-keystroke (autosaving would update the
  // draft → the left side of the diff → and the diff would vanish mid-typing).
  // When omitted, edits autosave to the agent draft via useDraftAutosave.
  onModifiedChange?: (value: string) => void;
}

const MonacoDiffEditorComponent = dynamic(
  () => import('@monaco-editor/react').then((mod) => mod.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center flex-1 min-h-50 text-xs text-muted-foreground gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading editor…
      </div>
    ),
  }
);

const LIGHT_THEME = 'connexity-diff-light';
const DARK_THEME = 'connexity-diff-dark';

// Tailwind green-500 / red-500 at 10% alpha — matches bg-green-500/10 and
// bg-red-500/10 on the original DiffView rows so the tint visually lines up.
const INSERTED_BG = '#22c55e1a';
const REMOVED_BG = '#ef44441a';
// Slightly stronger tint for word-level inline highlights inside a change.
const INSERTED_BG_STRONG = '#22c55e33';
const REMOVED_BG_STRONG = '#ef444433';

const handleBeforeMount: DiffBeforeMount = (monaco) => {
  monaco.editor.defineTheme(LIGHT_THEME, {
    base: 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#00000000',
      'editor.foreground': '#0a0a0a',
      'editorGutter.background': '#00000000',
      'editorLineNumber.foreground': '#a1a1aa',
      'diffEditor.insertedLineBackground': INSERTED_BG,
      'diffEditor.removedLineBackground': REMOVED_BG,
      'diffEditor.insertedTextBackground': INSERTED_BG_STRONG,
      'diffEditor.removedTextBackground': REMOVED_BG_STRONG,
      'diffEditor.border': '#00000000',
      'editorOverviewRuler.border': '#00000000',
    },
  });

  monaco.editor.defineTheme(DARK_THEME, {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#00000000',
      'editor.foreground': '#fafafa',
      'editorGutter.background': '#00000000',
      'editorLineNumber.foreground': '#52525b',
      'diffEditor.insertedLineBackground': INSERTED_BG,
      'diffEditor.removedLineBackground': REMOVED_BG,
      'diffEditor.insertedTextBackground': INSERTED_BG_STRONG,
      'diffEditor.removedTextBackground': REMOVED_BG_STRONG,
      'diffEditor.border': '#00000000',
      'editorOverviewRuler.border': '#00000000',
    },
  });
};

export function EditableDiffView({
  fromContent,
  toContent,
  editable,
  agentId,
  onModifiedChange,
}: EditableDiffViewProps) {
  // Presence of onModifiedChange switches the component into controlled mode:
  // no internal autosave, the parent owns every write.
  const isControlled = onModifiedChange !== undefined;
  const { resolvedTheme } = useTheme();
  const monacoTheme = resolvedTheme === 'dark' ? DARK_THEME : LIGHT_THEME;

  const editorRef = useRef<MonacoDiffEditor | null>(null);

  // Capture the toContent at mount and never update it, so the `modified`
  // prop handed to the library stays stable and its built-in setModel path
  // never fires. We handle all subsequent reconciliation imperatively below,
  // where we can suppress server echoes and preserve cursor position.
  const [initialModified] = useState(toContent);

  // Diff counts come from Monaco's own diff computation (via getLineChanges
  // inside onDidUpdateDiff) instead of re-computing with a separate diff
  // library. `total` is the modified-side line count — a more intuitive
  // "N lines" than the jsdiff-era sum of added+removed+unchanged hunks.
  const [counts, setCounts] = useState({ added: 0, removed: 0, total: 0 });

  // isPending is intentionally ignored here — the shared "Saving…" pill in
  // the agent header picks up this save via useIsMutating + the shared
  // mutation key on useUpsertDraft, so there's no per-surface spinner.
  const { schedule, flush, primeBaseline, getLastSaved } = useDraftAutosave(agentId);

  // Keep the latest `editable` flag + controlled-mode callback available to
  // the onDidChangeModelContent listener without having to re-subscribe it
  // on every flag flip.
  const editableRef = useRef(editable);
  useEffect(() => {
    editableRef.current = editable;
  }, [editable]);

  const isControlledRef = useRef(isControlled);
  const onModifiedChangeRef = useRef(onModifiedChange);
  useEffect(() => {
    isControlledRef.current = isControlled;
    onModifiedChangeRef.current = onModifiedChange;
  }, [isControlled, onModifiedChange]);

  useEffect(() => {
    // Autosave baseline is only meaningful when we actually own the draft
    // save path. In controlled mode the parent owns state, so skip priming.
    if (isControlled) return;
    primeBaseline(initialModified);
  }, [primeBaseline, initialModified, isControlled]);

  const handleMount: DiffOnMount = useCallback(
    (editor) => {
      editorRef.current = editor;
      const modifiedEditor = editor.getModifiedEditor();

      // Disable word-based suggestions on the modified (editable) side.
      // This option lives on the inner editor, not the diff editor's prop bag.
      modifiedEditor.updateOptions({ wordBasedSuggestions: 'off' });

      const recomputeCounts = () => {
        const lineChanges = editor.getLineChanges();
        const total = modifiedEditor.getModel()?.getLineCount() ?? 0;
        if (!lineChanges) {
          setCounts({ added: 0, removed: 0, total });
          return;
        }
        let added = 0;
        let removed = 0;
        for (const change of lineChanges) {
          if (change.modifiedEndLineNumber >= change.modifiedStartLineNumber) {
            added += change.modifiedEndLineNumber - change.modifiedStartLineNumber + 1;
          }
          if (change.originalEndLineNumber >= change.originalStartLineNumber) {
            removed += change.originalEndLineNumber - change.originalStartLineNumber + 1;
          }
        }
        setCounts({ added, removed, total });
      };

      // Fires after Monaco finishes (re)computing the diff — this is the
      // authoritative count source, driven by the same diff the editor is
      // rendering on screen.
      editor.onDidUpdateDiff(recomputeCounts);
      recomputeCounts();

      modifiedEditor.onDidChangeModelContent(() => {
        const value = modifiedEditor.getValue();
        if (!editableRef.current) return;
        if (isControlledRef.current) {
          onModifiedChangeRef.current?.(value);
        } else {
          schedule(value);
        }
      });
    },
    [schedule]
  );

  // Sync readOnly after mount when editable toggles (e.g. user switches the
  // right-side selector between `draft` and a historical version). Flush any
  // pending save first so the draft isn't left behind — only in the autosave
  // path; controlled mode has no internal buffer to flush.
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.updateOptions({ readOnly: !editable });
    if (!editable && !isControlled) {
      flush(editor.getModifiedEditor().getValue());
    }
  }, [editable, flush, isControlled]);

  // Imperatively reconcile external toContent updates with the live buffer.
  // Skips no-ops and, in autosave mode, echoes of our own save (react-query
  // invalidates and re-feeds the value we just wrote). In controlled mode
  // the parent owns toContent — every incoming value that differs from the
  // current buffer is legitimate (e.g. a fresh AI suggestion replacing the
  // previous one), so no echo suppression is needed.
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const modifiedEditor = editor.getModifiedEditor();
    const model = modifiedEditor.getModel();
    if (!model) return;
    const current = model.getValue();
    if (toContent === current) return;
    if (!isControlled && toContent === getLastSaved()) return;
    model.setValue(toContent);
  }, [toContent, getLastSaved, isControlled]);

  // Flush on unmount so navigating away mid-typing still persists the draft.
  // Controlled mode has nothing to flush — the parent is already sync with
  // every change via onModifiedChange.
  useEffect(() => {
    return () => {
      if (isControlledRef.current) return;
      const editor = editorRef.current;
      if (!editor) return;
      if (!editableRef.current) return;
      flush(editor.getModifiedEditor().getValue());
    };
  }, [flush]);

  // String compare (not Monaco counts) drives the "No differences" gate so
  // the empty state is correct on first render, before Monaco's async diff
  // computation has run. When editable, always mount Monaco so the user
  // can start typing immediately.
  const hasContentDifferences = fromContent !== toContent;

  if (!hasContentDifferences && !editable) {
    return (
      <div className="flex items-center justify-center border rounded-md bg-muted/20 py-10">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Check className="h-4 w-4 text-green-500" />
          No differences
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col border rounded-md overflow-hidden flex-1 min-h-80">
      <div className="flex items-center gap-3 px-3 py-2 border-b bg-muted/30 text-xs shrink-0">
        <span className="text-green-600 dark:text-green-400 font-medium">+{counts.added}</span>
        <span className="text-red-600 dark:text-red-400 font-medium">-{counts.removed}</span>
        <span className="text-muted-foreground">{counts.total} lines</span>
        {!editable && (
          <span className="ml-auto text-muted-foreground">Read-only</span>
        )}
      </div>
      <div className={cn('flex-1 min-h-0')}>
        <MonacoDiffEditorComponent
          original={fromContent}
          modified={initialModified}
          language="plaintext"
          theme={monacoTheme}
          beforeMount={handleBeforeMount}
          onMount={handleMount}
          height="100%"
          options={{
            renderSideBySide: false,
            originalEditable: false,
            readOnly: !editable,
            fontFamily:
              'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace)',
            fontSize: 12,
            lineNumbers: 'off',
            glyphMargin: false,
            folding: false,
            lineDecorationsWidth: 12,
            lineNumbersMinChars: 0,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            wordWrap: 'on',
            automaticLayout: true,
            renderLineHighlight: 'none',
            // Disable IntelliSense — there's no language server for plaintext
            // prompts, and word-based suggestions get in the user's way.
            // `wordBasedSuggestions` is an inner-editor option and is applied
            // imperatively in handleMount instead of through this prop bag.
            quickSuggestions: false,
            suggestOnTriggerCharacters: false,
            parameterHints: { enabled: false },
            snippetSuggestions: 'none',
            tabCompletion: 'off',
            renderIndicators: true,
            scrollbar: {
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8,
              useShadows: false,
            },
          }}
        />
      </div>
    </div>
  );
}
