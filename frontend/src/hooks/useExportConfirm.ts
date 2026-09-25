import { useState, useCallback } from 'react';
import { ExportHandoffSummary, ExportTarget } from '../types/export';

export function useExportConfirm() {
  const [isOpen, setIsOpen] = useState(false);
  const [summary, setSummary] = useState<ExportHandoffSummary | null>(null);
  const [resolve, setResolve] = useState<((target: ExportTarget) => void) | null>(null);

  const open = useCallback((s: ExportHandoffSummary): Promise<ExportTarget> => {
    setSummary(s);
    setIsOpen(true);
    return new Promise(r => setResolve(() => r));
  }, []);

  const confirm = useCallback((target: ExportTarget) => {
    resolve?.(target);
    setIsOpen(false);
    setResolve(null);
  }, [resolve]);

  const cancel = useCallback(() => {
    resolve?.(null as any);
    setIsOpen(false);
    setResolve(null);
  }, [resolve]);

  return { isOpen, summary, open, confirm, cancel };
}