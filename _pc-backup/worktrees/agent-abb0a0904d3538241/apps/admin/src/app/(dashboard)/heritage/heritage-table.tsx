'use client';

import { useMemo, useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ChevronLeft, ChevronRight, Eye, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { HeritageOut, HeritagePage } from '@/types/api';
import { deleteHeritageAction } from './actions';

interface FilterOption {
  readonly value: string;
  readonly label: string;
}

interface HeritageTableProps {
  readonly page: HeritagePage;
  readonly limit: number;
  readonly offset: number;
  readonly initialFilters: {
    readonly kind: string;
    readonly country: string;
    readonly status: string;
    readonly search: string;
  };
  readonly kindOptions: readonly FilterOption[];
  readonly countryOptions: readonly FilterOption[];
}

const STATUS_OPTIONS: readonly FilterOption[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'review', label: 'Review' },
  { value: 'published', label: 'Published' },
  { value: 'archived', label: 'Archived' },
  { value: 'rejected', label: 'Rejected' },
];

const ALL = '__all__';

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'published':
      return 'default';
    case 'review':
      return 'secondary';
    case 'rejected':
      return 'destructive';
    default:
      return 'outline';
  }
}

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? name.ru ?? Object.values(name)[0] ?? '—';
}

export function HeritageTable({
  page,
  limit,
  offset,
  initialFilters,
  kindOptions,
  countryOptions,
}: HeritageTableProps): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [filters, setFilters] = useState(initialFilters);
  const [sorting, setSorting] = useState<SortingState>([]);

  function applyFilters(next: typeof filters, nextOffset = 0): void {
    const params = new URLSearchParams(searchParams.toString());
    (['kind', 'country', 'status', 'search'] as const).forEach((key) => {
      const value = next[key];
      if (value) params.set(key, value);
      else params.delete(key);
    });
    if (nextOffset) params.set('offset', String(nextOffset));
    else params.delete('offset');
    startTransition(() => router.push(`/heritage?${params.toString()}`));
  }

  const columns = useMemo<ColumnDef<HeritageOut>[]>(() => {
    return [
      {
        id: 'name',
        header: 'Name',
        accessorFn: (row) => pickName(row.name),
        cell: ({ row }) => (
          <Link
            href={`/heritage/${row.original.pub_id}`}
            className="font-medium text-primary hover:underline"
          >
            {pickName(row.original.name)}
          </Link>
        ),
      },
      {
        id: 'kind',
        accessorKey: 'kind_slug',
        header: 'Kind',
        cell: ({ row }) => (
          <span className="text-sm capitalize text-muted-foreground">
            {row.original.kind_slug.replace(/_/g, ' ')}
          </span>
        ),
      },
      {
        id: 'country',
        accessorKey: 'country_code',
        header: 'Country',
        cell: ({ row }) => row.original.country_code ?? '—',
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Status',
        cell: ({ row }) => (
          <Badge variant={statusVariant(row.original.status)} className="capitalize">
            {row.original.status}
          </Badge>
        ),
      },
      {
        id: 'confidence',
        accessorKey: 'confidence_score',
        header: 'Confidence',
        cell: ({ row }) => `${row.original.confidence_score}%`,
      },
      {
        id: 'revision',
        accessorKey: 'revision',
        header: 'Rev.',
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Actions for ${pickName(row.original.name)}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/heritage/${row.original.pub_id}`}>
                  <Eye className="mr-2 h-4 w-4" /> View
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/heritage/${row.original.pub_id}#edit`}>
                  <Pencil className="mr-2 h-4 w-4" /> Edit
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onSelect={() => {
                  startTransition(async () => {
                    const result = await deleteHeritageAction(row.original.pub_id);
                    if (result.ok) toast.success('Heritage deleted');
                    else toast.error(result.message ?? 'Delete failed');
                  });
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ];
  }, []);

  const table = useReactTable({
    data: page.items as HeritageOut[],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const hasNext = offset + limit < page.total;
  const hasPrev = offset > 0;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Input
          placeholder="Search name / pub_id"
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          onKeyDown={(e) => {
            if (e.key === 'Enter') applyFilters(filters);
          }}
          aria-label="Search heritage"
        />
        <Select
          value={filters.kind || ALL}
          onValueChange={(v) => {
            const next = { ...filters, kind: v === ALL ? '' : v };
            setFilters(next);
            applyFilters(next);
          }}
        >
          <SelectTrigger aria-label="Filter by kind">
            <SelectValue placeholder="All kinds" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All kinds</SelectItem>
            {kindOptions.map((k) => (
              <SelectItem key={k.value} value={k.value}>
                {k.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.country || ALL}
          onValueChange={(v) => {
            const next = { ...filters, country: v === ALL ? '' : v };
            setFilters(next);
            applyFilters(next);
          }}
        >
          <SelectTrigger aria-label="Filter by country">
            <SelectValue placeholder="All countries" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All countries</SelectItem>
            {countryOptions.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.status || ALL}
          onValueChange={(v) => {
            const next = { ...filters, status: v === ALL ? '' : v };
            setFilters(next);
            applyFilters(next);
          }}
        >
          <SelectTrigger aria-label="Filter by status">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          onClick={() => {
            const cleared = { kind: '', country: '', status: '', search: '' };
            setFilters(cleared);
            applyFilters(cleared);
          }}
        >
          Reset
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className={
                      header.column.getCanSort() ? 'cursor-pointer select-none' : ''
                    }
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-muted-foreground"
                >
                  No heritage found for this filter set.
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {offset + 1}–{Math.min(offset + limit, page.total)} of {page.total}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!hasPrev || pending}
            onClick={() => applyFilters(filters, Math.max(0, offset - limit))}
          >
            <ChevronLeft className="h-4 w-4" /> Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasNext || pending}
            onClick={() => applyFilters(filters, offset + limit)}
          >
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
