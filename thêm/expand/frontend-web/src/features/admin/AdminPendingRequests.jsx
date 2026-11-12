import React, { useState, useEffect } from 'react';
import { Check, X, UserCheck, ShieldAlert, Phone, Mail, Clock } from 'lucide-react';
import { schoolService } from '../../services/schoolService';
import { Button } from '../../components/common/Button';

export function AdminPendingRequests({ schoolId }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRequests = async () => {
    if (!schoolId) return;
    setLoading(true);
    try {
      const res = await schoolService.getPendingRequests(schoolId);
      setRequests(res.data || []);
    } catch {
      setRequests([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [schoolId]);

  const handleAction = async (requestId, action) => {
    const confirmMsg = action === 'approve'
      ? 'Bạn có chắc chắn muốn phê duyệt thành viên này?'
      : 'Bạn có chắc chắn muốn từ chối yêu cầu này?';
    if (!window.confirm(confirmMsg)) return;

    try {
      await schoolService.handleRequestAction(requestId, action);
      // Optimistic UI update
      setRequests((prev) => prev.filter((r) => r.id !== requestId));
    } catch (err) {
      alert(err.message || 'Lỗi xử lý yêu cầu.');
    }
  };

  return (
    <div className="bg-[#1a1d27] border border-white/10 rounded-2xl p-6 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div className="flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-purple-400" />
          <h3 className="font-bold text-white text-base">Danh Sách Chờ Duyệt Thành Viên</h3>
        </div>
        <span className="text-xs bg-purple-500/20 text-purple-300 font-bold px-2.5 py-1 rounded-full border border-purple-500/30">
          {requests.length} yêu cầu
        </span>
      </div>

      <div className="space-y-3">
        {loading ? (
          <div className="py-8 text-center text-gray-300 text-sm">Đang tải danh sách...</div>
        ) : requests.length === 0 ? (
          <div className="py-8 text-center text-gray-300 text-sm">
            Hiện không có đơn xin gia nhập nào đang chờ xét duyệt.
          </div>
        ) : (
          requests.map((item) => (
            <div
              key={item.id}
              className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition hover:bg-white/[0.07]"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h4 className="font-semibold text-white text-sm">{item.user?.fullName}</h4>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {item.user?.role}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">(@{item.user?.username})</span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-gray-300">
                  <span>Mã định danh: <code className="text-blue-400 font-mono font-semibold">{item.user?.memberCode}</code></span>
                  {item.user?.phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="w-3 h-3 text-gray-400" />
                      {item.user.phone}
                    </span>
                  )}
                  {item.user?.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="w-3 h-3 text-gray-400" />
                      {item.user.email}
                    </span>
                  )}
                  {item.createdAt && (
                    <span className="flex items-center gap-1 text-gray-400">
                      <Clock className="w-3 h-3" />
                      {new Date(item.createdAt).toLocaleString('vi-VN')}
                    </span>
                  )}
                </div>
              </div>

              {/* 1-Click Approve & 1-Click Reject */}
              <div className="flex items-center gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleAction(item.id, 'reject')}
                  className="cursor-pointer transition"
                >
                  <X className="w-3.5 h-3.5" /> Từ chối
                </Button>
                <Button
                  variant="success"
                  size="sm"
                  onClick={() => handleAction(item.id, 'approve')}
                  className="cursor-pointer transition"
                >
                  <Check className="w-3.5 h-3.5" /> Chấp thuận
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
