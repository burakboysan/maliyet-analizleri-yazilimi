import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  CalendarPlus,
  Check,
  CircleCheck,
  Loader2,
  Send,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import {
  approveLeaveRequest,
  cancelLeaveRequest,
  createLeaveRequest,
  fetchLeaveDashboard,
  fetchLeaveWorkdaySummary,
  finalizeLeaveRequest,
  markLeaveUsageConfirmation,
  rejectLeaveRequest,
  type LeaveApprovePayload,
  type LeaveRequestInfo,
} from "../lib/api";
import { formatDate, formatNumber } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Skeleton } from "../components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";

export const Route = createFileRoute("/_authenticated/leave-management")({
  head: () => ({ meta: [{ title: "İzin Yönetimi — Bomaksan" }] }),
  component: LeavePage,
});

const LEAVE_TYPES: Array<{ value: string; label: string }> = [
  { value: "YILLIK_IZIN", label: "Yıllık İzin" },
  { value: "MAZERET_IZNI", label: "Mazeret İzni" },
  { value: "UCRETSIZ_IZIN", label: "Ücretsiz İzin" },
  { value: "RAPORLU", label: "Raporlu (Sağlık)" },
];

const STATUS_META: Record<string, { label: string; className: string }> = {
  ONAY_BEKLIYOR: { label: "Onay Bekliyor", className: "bg-amber-500/15 text-amber-400" },
  BEKLIYOR: { label: "Onay Bekliyor", className: "bg-amber-500/15 text-amber-400" },
  YONETICI_ONAYI_BEKLIYOR: {
    label: "Yönetici Onayı Bekliyor",
    className: "bg-amber-500/15 text-amber-400",
  },
  ONAYLANDI: { label: "Onaylandı", className: "bg-emerald-500/15 text-emerald-400" },
  REDDEDILDI: { label: "Reddedildi", className: "bg-destructive/15 text-destructive" },
  IPTAL_EDILDI: { label: "İptal Edildi", className: "bg-secondary text-muted-foreground" },
  KULLANIM_ONAYI_BEKLIYOR: {
    label: "Kullanım Onayı Bekliyor",
    className: "bg-sky-500/15 text-sky-400",
  },
  TAMAMLANDI: { label: "Tamamlandı", className: "bg-emerald-500/15 text-emerald-400" },
};

function statusMeta(status?: string | null) {
  if (!status) return { label: "—", className: "bg-secondary text-muted-foreground" };
  return (
    STATUS_META[status] ?? {
      label: status.replace(/_/g, " "),
      className: "bg-secondary text-muted-foreground",
    }
  );
}

function leaveTypeLabel(value?: string | null) {
  if (!value) return "—";
  const found = LEAVE_TYPES.find((t) => t.value === value);
  if (found) return found.label;
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const APPROVAL_PENDING = new Set([
  "ONAY_BEKLIYOR",
  "BEKLIYOR",
  "YONETICI_ONAYI_BEKLIYOR",
]);

function LeavePage() {
  const { token } = useAuth();
  const dashQuery = useQuery({
    queryKey: ["leave-dashboard"],
    queryFn: () => fetchLeaveDashboard(token!),
    enabled: !!token,
  });

  const data = dashQuery.data;
  const balance = data?.balance;

  return (
    <div className="space-y-8 p-8">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <BalanceCard
          label="Kullanılabilir"
          value={balance?.available_days}
          loading={dashQuery.isLoading}
          accent
        />
        <BalanceCard
          label="Rezerve"
          value={balance?.reserved_days}
          loading={dashQuery.isLoading}
        />
        <BalanceCard
          label="Kullanılan"
          value={balance?.used_days}
          loading={dashQuery.isLoading}
        />
        <BalanceCard
          label="Onay Bekleyen"
          value={balance?.pending_approval_days}
          loading={dashQuery.isLoading}
        />
      </div>

      {balance && (
        <p className="-mt-4 font-mono text-xs text-muted-foreground">
          Yıllık hak: {formatNumber(balance.annual_allowance_days, 1)} gün · Devreden:{" "}
          {formatNumber(balance.carried_over_days, 1)} gün
        </p>
      )}

      <NewLeaveRequest />

      <RequestTable
        title="İzin Taleplerim"
        requests={data?.my_requests}
        loading={dashQuery.isLoading}
        variant="mine"
      />

      {(dashQuery.isLoading ||
        (data?.pending_manager_requests?.length ?? 0) > 0) && (
        <RequestTable
          title="Onayımı Bekleyenler"
          requests={data?.pending_manager_requests}
          loading={dashQuery.isLoading}
          variant="manager"
        />
      )}
    </div>
  );
}

function BalanceCard({
  label,
  value,
  loading,
  accent,
}: {
  label: string;
  value?: number | null;
  loading: boolean;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="font-mono text-[10px] uppercase tracking-tighter text-muted-foreground">
        {label}
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-8 w-16" />
      ) : (
        <div
          className={cn(
            "mt-1 font-display text-2xl font-bold",
            accent && "text-primary",
          )}
        >
          {formatNumber(value, 1)}
          <span className="ml-1 text-sm font-normal text-muted-foreground">gün</span>
        </div>
      )}
    </div>
  );
}

function NewLeaveRequest() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [leaveType, setLeaveType] = useState("YILLIK_IZIN");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [requestedDays, setRequestedDays] = useState("");
  const [daysTouched, setDaysTouched] = useState(false);
  const [reason, setReason] = useState("");
  const [employeeNote, setEmployeeNote] = useState("");

  const rangeValid = !!startDate && !!endDate && startDate <= endDate;

  const workdayQuery = useQuery({
    queryKey: ["leave-workday", startDate, endDate],
    queryFn: () => fetchLeaveWorkdaySummary(token!, startDate, endDate),
    enabled: !!token && rangeValid,
  });

  // Auto-fill requested days from workday summary until the user edits it.
  useEffect(() => {
    if (!daysTouched && workdayQuery.data) {
      setRequestedDays(String(workdayQuery.data.work_days));
    }
  }, [workdayQuery.data, daysTouched]);

  const resetForm = () => {
    setLeaveType("YILLIK_IZIN");
    setStartDate("");
    setEndDate("");
    setRequestedDays("");
    setDaysTouched(false);
    setReason("");
    setEmployeeNote("");
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createLeaveRequest(token!, {
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        requested_days: Number(requestedDays) || 0,
        reason: reason.trim() || null,
        employee_note: employeeNote.trim() || null,
      }),
    onSuccess: () => {
      toast.success("İzin talebi oluşturuldu.");
      queryClient.invalidateQueries({ queryKey: ["leave-dashboard"] });
      resetForm();
      setOpen(false);
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Talep oluşturulamadı.");
    },
  });

  const canSubmit =
    rangeValid && Number(requestedDays) > 0 && !createMutation.isPending;

  if (!open) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-dashed border-border bg-surface px-6 py-5">
        <div>
          <h2 className="font-display font-bold tracking-tight">Yeni İzin Talebi</h2>
          <p className="text-sm text-muted-foreground">
            Tarih aralığı seçin; iş günü otomatik hesaplanır.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <CalendarPlus className="size-4" />
          Talep Oluştur
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h2 className="font-display font-bold tracking-tight">Yeni İzin Talebi</h2>
        <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
          <X className="size-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-2">
        <div className="space-y-2">
          <Label>İzin Türü</Label>
          <Select value={leaveType} onValueChange={setLeaveType}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEAVE_TYPES.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>
            Talep Edilen Gün
            {workdayQuery.isFetching && (
              <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                hesaplanıyor…
              </span>
            )}
          </Label>
          <Input
            value={requestedDays}
            inputMode="decimal"
            onChange={(e) => {
              setDaysTouched(true);
              setRequestedDays(e.target.value);
            }}
            placeholder="0"
          />
          {rangeValid && workdayQuery.data && (
            <p className="font-mono text-[10px] text-muted-foreground">
              Aralıktaki iş günü: {formatNumber(workdayQuery.data.work_days, 1)}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Başlangıç</Label>
          <Input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setDaysTouched(false);
            }}
          />
        </div>

        <div className="space-y-2">
          <Label>Bitiş</Label>
          <Input
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(e) => {
              setEndDate(e.target.value);
              setDaysTouched(false);
            }}
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label>Gerekçe</Label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="İzin gerekçesi"
            rows={2}
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label>Personel Notu</Label>
          <Textarea
            value={employeeNote}
            onChange={(e) => setEmployeeNote(e.target.value)}
            placeholder="Eklemek istediğiniz not (opsiyonel)"
            rows={2}
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
        <Button variant="outline" onClick={() => setOpen(false)}>
          Vazgeç
        </Button>
        <Button onClick={() => createMutation.mutate()} disabled={!canSubmit}>
          {createMutation.isPending && <Loader2 className="size-4 animate-spin" />}
          <Send className="size-4" />
          Talebi Gönder
        </Button>
      </div>
    </div>
  );
}

function RequestTable({
  title,
  requests,
  loading,
  variant,
}: {
  title: string;
  requests?: LeaveRequestInfo[];
  loading: boolean;
  variant: "mine" | "manager";
}) {
  const showUser = variant === "manager";
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-6 py-4">
        <h2 className="font-display font-bold tracking-tight">{title}</h2>
      </div>
      {loading ? (
        <div className="space-y-2 p-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : !requests || requests.length === 0 ? (
        <div className="p-10 text-center text-sm text-muted-foreground">
          Kayıt bulunmuyor.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                {showUser && <th className="px-6 py-3 font-medium">Personel</th>}
                <th className="px-6 py-3 font-medium">Tür</th>
                <th className="px-4 py-3 font-medium">Başlangıç</th>
                <th className="px-4 py-3 font-medium">Bitiş</th>
                <th className="px-4 py-3 text-right font-medium">Gün</th>
                <th className="px-6 py-3 font-medium">Durum</th>
                <th className="px-6 py-3 text-right font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {requests.map((r) => (
                <RequestRow
                  key={r.id}
                  request={r}
                  showUser={showUser}
                  variant={variant}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RequestRow({
  request: r,
  showUser,
  variant,
}: {
  request: LeaveRequestInfo;
  showUser: boolean;
  variant: "mine" | "manager";
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const meta = statusMeta(r.status);
  const status = r.status ?? "";

  const [confirmCancel, setConfirmCancel] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [finalizeOpen, setFinalizeOpen] = useState(false);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["leave-dashboard"] });

  const cancelMutation = useMutation({
    mutationFn: () => cancelLeaveRequest(token!, r.id),
    onSuccess: () => {
      toast.success("Talep iptal edildi.");
      invalidate();
      setConfirmCancel(false);
    },
    onError: (e: unknown) => {
      toast.error(e instanceof Error ? e.message : "İptal başarısız.");
      setConfirmCancel(false);
    },
  });

  const usageMutation = useMutation({
    mutationFn: () => markLeaveUsageConfirmation(token!, r.id),
    onSuccess: () => {
      toast.success("Kullanım onayı istendi.");
      invalidate();
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "İşlem başarısız."),
  });

  const canCancel =
    variant === "mine" &&
    !["IPTAL_EDILDI", "REDDEDILDI", "TAMAMLANDI"].includes(status);

  const isApprovalPending = APPROVAL_PENDING.has(status);
  const isUsagePending = status === "KULLANIM_ONAYI_BEKLIYOR";
  const isApproved = status === "ONAYLANDI";

  return (
    <>
      <tr className="hover:bg-accent">
        {showUser && (
          <td className="px-6 py-3 font-medium">{r.user_name ?? "—"}</td>
        )}
        <td className="px-6 py-3">{leaveTypeLabel(r.leave_type)}</td>
        <td className="px-4 py-3 font-mono text-xs">{formatDate(r.start_date)}</td>
        <td className="px-4 py-3 font-mono text-xs">{formatDate(r.end_date)}</td>
        <td className="px-4 py-3 text-right font-mono">
          {formatNumber(r.actual_used_days ?? r.approved_days ?? r.requested_days, 1)}
        </td>
        <td className="px-6 py-3">
          <span
            className={cn(
              "rounded-full px-2 py-0.5 font-mono text-[10px] uppercase",
              meta.className,
            )}
          >
            {meta.label}
          </span>
        </td>
        <td className="px-6 py-3">
          <div className="flex justify-end gap-2">
            {variant === "mine" && canCancel && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmCancel(true)}
              >
                İptal Et
              </Button>
            )}
            {variant === "manager" && isApprovalPending && (
              <>
                <Button size="sm" onClick={() => setApproveOpen(true)}>
                  <Check className="size-3.5" /> Onayla
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setRejectOpen(true)}
                >
                  Reddet
                </Button>
              </>
            )}
            {variant === "manager" && isApproved && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => usageMutation.mutate()}
                disabled={usageMutation.isPending}
              >
                {usageMutation.isPending && (
                  <Loader2 className="size-3.5 animate-spin" />
                )}
                Kullanım Onayı İste
              </Button>
            )}
            {variant === "manager" && isUsagePending && (
              <Button size="sm" onClick={() => setFinalizeOpen(true)}>
                <CircleCheck className="size-3.5" /> Kesinleştir
              </Button>
            )}
            {variant === "manager" &&
              !isApprovalPending &&
              !isApproved &&
              !isUsagePending && (
                <span className="text-xs text-muted-foreground">—</span>
              )}
          </div>
        </td>
      </tr>

      <AlertDialog open={confirmCancel} onOpenChange={setConfirmCancel}>
        <AlertDialogContent className="border-border bg-surface">
          <AlertDialogHeader>
            <AlertDialogTitle>Talebi iptal et?</AlertDialogTitle>
            <AlertDialogDescription>
              {formatDate(r.start_date)} – {formatDate(r.end_date)} tarihli izin
              talebi iptal edilecek.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                cancelMutation.mutate();
              }}
              disabled={cancelMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {cancelMutation.isPending && (
                <Loader2 className="size-4 animate-spin" />
              )}
              İptal Et
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ApproveDialog
        request={r}
        open={approveOpen}
        onOpenChange={setApproveOpen}
        onDone={invalidate}
      />
      <RejectDialog
        request={r}
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        onDone={invalidate}
      />
      <FinalizeDialog
        request={r}
        open={finalizeOpen}
        onOpenChange={setFinalizeOpen}
        onDone={invalidate}
      />
    </>
  );
}

function ApproveDialog({
  request: r,
  open,
  onOpenChange,
  onDone,
}: {
  request: LeaveRequestInfo;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const { token } = useAuth();
  const [mode, setMode] =
    useState<LeaveApprovePayload["approval_mode"]>("BAKIYEDEN_DUSECEK");
  const [approvedDays, setApprovedDays] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (open) {
      setMode("BAKIYEDEN_DUSECEK");
      setApprovedDays(String(r.requested_days ?? ""));
      setNote("");
    }
  }, [open, r.requested_days]);

  const mutation = useMutation({
    mutationFn: () =>
      approveLeaveRequest(token!, r.id, {
        approval_mode: mode,
        approved_days: approvedDays === "" ? null : Number(approvedDays),
        manager_note: note.trim() || null,
      }),
    onSuccess: () => {
      toast.success("Talep onaylandı.");
      onDone();
      onOpenChange(false);
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Onay başarısız."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-surface">
        <DialogHeader>
          <DialogTitle>İzin Talebini Onayla</DialogTitle>
          <DialogDescription>
            {r.user_name} · {formatDate(r.start_date)} – {formatDate(r.end_date)}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Onay Modu</Label>
            <Select
              value={mode}
              onValueChange={(v) =>
                setMode(v as LeaveApprovePayload["approval_mode"])
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BAKIYEDEN_DUSECEK">
                  Bakiyeden Düşülecek
                </SelectItem>
                <SelectItem value="YONETICI_IZNI">Yönetici İzni</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Onaylanan Gün</Label>
            <Input
              value={approvedDays}
              inputMode="decimal"
              onChange={(e) => setApprovedDays(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Yönetici Notu</Label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="Opsiyonel"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Onayla
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RejectDialog({
  request: r,
  open,
  onOpenChange,
  onDone,
}: {
  request: LeaveRequestInfo;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const { token } = useAuth();
  const [note, setNote] = useState("");

  useEffect(() => {
    if (open) setNote("");
  }, [open]);

  const mutation = useMutation({
    mutationFn: () => rejectLeaveRequest(token!, r.id, note),
    onSuccess: () => {
      toast.success("Talep reddedildi.");
      onDone();
      onOpenChange(false);
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Red başarısız."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-surface">
        <DialogHeader>
          <DialogTitle>İzin Talebini Reddet</DialogTitle>
          <DialogDescription>
            {r.user_name} · {formatDate(r.start_date)} – {formatDate(r.end_date)}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>Red Gerekçesi</Label>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            placeholder="Reddetme gerekçesi (opsiyonel)"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button
            variant="destructive"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Reddet
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function FinalizeDialog({
  request: r,
  open,
  onOpenChange,
  onDone,
}: {
  request: LeaveRequestInfo;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const { token } = useAuth();
  const [actualDays, setActualDays] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (open) {
      setActualDays(String(r.approved_days ?? r.requested_days ?? ""));
      setNote("");
    }
  }, [open, r.approved_days, r.requested_days]);

  const mutation = useMutation({
    mutationFn: () =>
      finalizeLeaveRequest(token!, r.id, Number(actualDays) || 0, note),
    onSuccess: () => {
      toast.success("İzin kullanımı kesinleştirildi.");
      onDone();
      onOpenChange(false);
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Kesinleştirme başarısız."),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-surface">
        <DialogHeader>
          <DialogTitle>Kullanımı Kesinleştir</DialogTitle>
          <DialogDescription>
            {r.user_name} · {formatDate(r.start_date)} – {formatDate(r.end_date)}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Gerçekleşen Gün</Label>
            <Input
              value={actualDays}
              inputMode="decimal"
              onChange={(e) => setActualDays(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Yönetici Notu</Label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="Opsiyonel"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="size-4 animate-spin" />}
            Kesinleştir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
