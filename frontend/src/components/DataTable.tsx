import { useState } from 'react';
import type { ReactNode } from 'react';
import Icon from './Icon';

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  isRowSaved?: (row: T) => boolean;
}

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  isRowSaved,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [dir, setDir] = useState<'asc' | 'desc'>('desc');

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setDir('desc');
    }
  };

  const sorted = [...rows];
  if (sortKey) {
    const col = columns.find((c) => c.key === sortKey);
    const sv = col?.sortValue;
    if (sv) {
      sorted.sort((a, b) => {
        const va = sv(a);
        const vb = sv(b);
        if (typeof va === 'number' && typeof vb === 'number') {
          return dir === 'asc' ? va - vb : vb - va;
        }
        const sa = String(va).toLowerCase();
        const sb = String(vb).toLowerCase();
        const cmp = sa < sb ? -1 : sa > sb ? 1 : 0;
        return dir === 'asc' ? cmp : -cmp;
      });
    }
  }

  return (
    <div className="table-card">
      <table className="tbl">
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                onClick={() => c.sortValue && toggleSort(c.key)}
                className={`${c.className ?? ''} ${c.sortValue ? 'sortable' : ''}`}
              >
                {c.header}
                {c.sortValue && (
                  <span className="sort">
                    <Icon name="chevronUp" className={sortKey === c.key && dir === 'asc' ? 'on' : ''} />
                    <Icon name="chevronDown" className={sortKey === c.key && dir === 'desc' ? 'on' : ''} />
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={() => onRowClick?.(row)}
              className={isRowSaved?.(row) ? 'saved' : undefined}
            >
              {columns.map((c) => (
                <td key={c.key} className={c.className}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
