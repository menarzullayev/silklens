import * as React from 'react';

/**
 * Lightweight server-renderable table wrapper for simple list views.
 *
 * Use this when you need a quick read-only table without TanStack Table's
 * client-side sorting/filtering. For interactive tables with column
 * visibility, sorting, and search, use `DataTable` from
 * `@/components/data-table/data-table` instead.
 */

export interface Column<T> {
  /** Used as a React key and as the default property accessor when `render` is absent. */
  readonly key: string;
  readonly header: string;
  readonly render?: (row: T) => React.ReactNode;
}

export interface DataTableSimpleProps<T> {
  readonly columns: Column<T>[];
  readonly data: T[];
  readonly emptyMessage?: string;
  /** Optional caption for screen-reader accessibility. */
  readonly caption?: string;
}

export function DataTableSimple<T extends { id: string }>({
  columns,
  data,
  emptyMessage = 'No data',
  caption,
}: DataTableSimpleProps<T>): React.ReactElement {
  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <table className="w-full text-sm">
        {caption ? (
          <caption className="sr-only">{caption}</caption>
        ) : null}
        <thead className="border-b bg-muted/50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className="px-4 py-3 text-left font-medium text-muted-foreground"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={row.id}
                className="border-b last:border-0 hover:bg-muted/20 transition-colors"
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3">
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
