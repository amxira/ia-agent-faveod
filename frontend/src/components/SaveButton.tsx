import { useMemo } from 'react';
import { useSaved, useSaveItem, useUnsaveItem } from '../hooks';
import Icon from './Icon';

// A hook that tells whether an item is bookmarked and toggles it.
export function useIsSaved(kind: 'tenders' | 'partners' | 'leads', id?: string) {
  const { data } = useSaved();
  const save = useSaveItem();
  const unsave = useUnsaveItem();

  const saved = useMemo(() => {
    if (!id || !data) return false;
    const resolved = data[kind];
    const key = kind === 'tenders' ? 'tender_id' : kind === 'partners' ? 'partner_id' : 'lead_id';
    return resolved.items.some((item) => (item as unknown as Record<string, unknown>)[key] === id);
  }, [data, kind, id]);

  const toggle = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!id) return;
    if (saved) void unsave.mutate({ kind, id });
    else void save.mutate({ kind, id });
  };

  const busy = save.isPending || unsave.isPending;
  return { saved, toggle, busy };
}

export function SaveButton({
  kind,
  id,
  label = true,
}: {
  kind: 'tenders' | 'partners' | 'leads';
  id?: string;
  label?: boolean;
}) {
  const { saved, toggle, busy } = useIsSaved(kind, id);
  return (
    <button
      className={`btn btn-sm ${saved ? 'btn-danger' : 'btn-soft'}`}
      onClick={toggle}
      disabled={busy || !id}
      title={saved ? 'Retirer des favoris' : 'Ajouter aux favoris'}
    >
      <Icon name="star" size={14} style={saved ? { fill: 'currentColor' } : undefined} />
      {label && (saved ? 'Enregistré' : 'Enregistrer')}
    </button>
  );
}
