import React, { useState, useEffect, useRef } from 'react';
import { useRoleAccess } from '../../hooks/useRoleAccess';
import { AdminPendingRequests } from '../admin/AdminPendingRequests';
import { SchoolMemberManagement } from '../admin/SchoolMemberManagement';
import { StudentQRCard } from '../student/StudentQRCard';
import { ParentChildTimeline } from '../parent/ParentChildTimeline';
import { ClassHub } from '../classes/ClassHub';
import { HonorBoard } from '../honor/HonorBoard';
import {
  MessageSquare, Heart, Share2, Calendar, Trash2,
  Loader2, ImagePlus, Megaphone, Send, School,
  AlertCircle, CheckCircle2, Sparkles, Clock
} from 'lucide-react';
import { postService } from '../../services/postService';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Trả về thời gian thân thiện: "Vừa xong", "5 phút trước", "Hôm qua lúc 07:15" */
function friendlyTime(dateStr) {
  if (!dateStr) return '';
  const now  = new Date();
  const then = new Date(dateStr);
  const diffMs  = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  const diffH   = Math.floor(diffMin / 60);
  const diffD   = Math.floor(diffH / 24);

  if (diffMin < 1)  return 'Vừa xong';
  if (diffMin < 60) return `${diffMin} phút trước`;
  if (diffH < 24)   return `${diffH} giờ trước`;
  if (diffD === 1) {
    const hhmm = then.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    return `Hôm qua lúc ${hhmm}`;
  }
  return then.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/** Lấy 2 chữ cái viết tắt từ tên */
function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || '?';
}

/** Màu avatar theo role */
const ROLE_AVATAR = {
  HEADMASTER:    'from-rose-500 to-red-600',
  SCHOOL_ADMIN:  'from-rose-500 to-red-600',
  TEACHER:       'from-violet-500 to-purple-600',
  INSPECTOR:     'from-orange-500 to-amber-500',
  STUDENT:       'from-sky-500 to-blue-500',
  PARENT:        'from-emerald-500 to-teal-500',
  ADMIN:         'from-red-600 to-pink-600',
  PLATFORM_ADMIN:'from-red-600 to-pink-600',
};

const ROLE_TAG = {
  HEADMASTER: { label: 'Hiệu Trưởng', cls: 'bg-rose-500/15 text-rose-400 border-rose-500/30' },
  SCHOOL_ADMIN: { label: 'Quản Lý',   cls: 'bg-rose-500/15 text-rose-400 border-rose-500/30' },
  TEACHER:    { label: 'Giáo Viên',   cls: 'bg-violet-500/15 text-violet-400 border-violet-500/30' },
  INSPECTOR:  { label: 'Giám Thị',    cls: 'bg-orange-500/15 text-orange-400 border-orange-500/30' },
  STUDENT:    { label: 'Học Sinh',    cls: 'bg-sky-500/15 text-sky-400 border-sky-500/30' },
  PARENT:     { label: 'Phụ Huynh',  cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  ADMIN:      { label: 'Super Admin', cls: 'bg-red-500/15 text-red-400 border-red-500/30' },
  PLATFORM_ADMIN: { label: 'Super Admin', cls: 'bg-red-500/15 text-red-400 border-red-500/30' },
};

const MAX_CHARS = 500;

// ─── Skeleton Loader ──────────────────────────────────────────────────────────
function PostSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-5 space-y-4 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-white/10" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-32 bg-white/10 rounded-full" />
          <div className="h-2.5 w-20 bg-white/5 rounded-full" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-white/10 rounded-full w-full" />
        <div className="h-3 bg-white/10 rounded-full w-5/6" />
        <div className="h-3 bg-white/10 rounded-full w-3/4" />
      </div>
      <div className="flex gap-4 pt-2 border-t border-white/5">
        <div className="h-3 w-16 bg-white/5 rounded-full" />
        <div className="h-3 w-20 bg-white/5 rounded-full" />
        <div className="h-3 w-12 bg-white/5 rounded-full ml-auto" />
      </div>
    </div>
  );
}

// ─── Empty State SVG ──────────────────────────────────────────────────────────
function EmptyFeedState({ canPost }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-5">
      {/* Inline SVG illustration */}
      <svg width="120" height="100" viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-60">
        <rect x="10" y="20" width="100" height="64" rx="10" fill="#1e2235" stroke="#3b4a6b" strokeWidth="1.5"/>
        <rect x="22" y="34" width="52" height="6" rx="3" fill="#3b4a6b"/>
        <rect x="22" y="46" width="76" height="4" rx="2" fill="#2a3352"/>
        <rect x="22" y="55" width="64" height="4" rx="2" fill="#2a3352"/>
        <rect x="22" y="64" width="40" height="4" rx="2" fill="#2a3352"/>
        <circle cx="95" cy="30" r="16" fill="#0f1117" stroke="#3b4a6b" strokeWidth="1.5"/>
        <path d="M89 30 L93 34 L101 26" stroke="#4f7fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M60 9 L63 15 L57 15 Z" fill="#3b4a6b"/>
        <circle cx="18" cy="85" r="5" fill="#1e2235" stroke="#3b4a6b" strokeWidth="1.5"/>
        <circle cx="105" cy="14" r="3" fill="#2a3352"/>
      </svg>

      <div className="text-center space-y-2 max-w-xs">
        <h4 className="text-[15px] font-bold text-white flex items-center justify-center gap-2">
          <span>Bảng tin đang chờ bạn!</span>
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
        </h4>
        <p className="text-sm text-gray-300 leading-relaxed">
          {canPost
            ? 'Hãy là người đầu tiên đăng thông báo để kết nối với toàn trường.'
            : 'Thầy cô và Ban Giám Hiệu sẽ sớm gửi thông báo mới nhất tại đây.'}
        </p>
      </div>

      {canPost && (
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium">
          <Megaphone className="w-3.5 h-3.5" />
          Soạn thông báo đầu tiên ngay bên trên ↑
        </div>
      )}
    </div>
  );
}

// ─── Post Card ────────────────────────────────────────────────────────────────
function PostCard({ post, currentUser, onLike, onDelete }) {
  const [likeAnim, setLikeAnim] = useState(false);
  const [copied, setCopied]     = useState(false);

  const canDelete =
    ['ADMIN', 'PLATFORM_ADMIN', 'HEADMASTER'].includes(currentUser?.role) ||
    (currentUser?.id && post.authorId === currentUser?.id);

  const role      = post.authorRole || 'STUDENT';
  const avatarGrad = ROLE_AVATAR[role] || ROLE_AVATAR.STUDENT;
  const tagConf   = ROLE_TAG[role] || ROLE_TAG.STUDENT;

  const handleLike = () => {
    setLikeAnim(true);
    onLike(post.id);
    setTimeout(() => setLikeAnim(false), 300);
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="group bg-white/[0.03] hover:bg-white/[0.05] border border-white/[0.07] hover:border-white/[0.12] rounded-2xl overflow-hidden transition-all duration-200 shadow-sm hover:shadow-md hover:shadow-black/20">
      {/* Card Body */}
      <div className="p-5 space-y-4">
        {/* Author Row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${avatarGrad} flex items-center justify-center text-white text-sm font-extrabold shadow-md shrink-0`}>
              {post.avatarText || getInitials(post.author)}
            </div>
            <div>
              <h4 className="text-sm font-bold text-white leading-none">{post.author}</h4>
              <p className="text-xs text-gray-400 mt-1 flex items-center gap-1.5">
                <span>{friendlyTime(post.createdAt || post.timeText)}</span>
              </p>
            </div>
          </div>

          {/* Right: Role Tag + Delete */}
          <div className="flex items-center gap-2 shrink-0">
            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase border ${tagConf.cls}`}>
              {post.roleTag || tagConf.label}
            </span>
            {canDelete && (
              <button
                onClick={() => onDelete(post.id)}
                className="p-1 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition cursor-pointer"
                title="Xóa bài viết"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Text Content */}
        <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">{post.content}</p>
      </div>

      {/* Card Actions Footer */}
      <div className="px-5 py-3 border-t border-white/[0.05] bg-white/[0.01] flex items-center justify-between">
        <button
          onClick={handleLike}
          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all duration-150 cursor-pointer ${
            post.isLiked
              ? 'text-rose-400 bg-rose-500/10'
              : 'text-gray-400 hover:text-rose-400 hover:bg-rose-500/10'
          }`}
        >
          <Heart
            className={`w-4 h-4 transition-transform duration-200 ${
              likeAnim ? 'scale-125 fill-rose-400' : post.isLiked ? 'fill-rose-400' : ''
            }`}
          />
          <span>{post.likesCount || 0}</span>
        </button>

        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 text-xs font-medium text-gray-400 hover:text-white px-3 py-1.5 rounded-xl hover:bg-white/5 transition cursor-pointer"
        >
          <Share2 className="w-3.5 h-3.5" />
          <span>{copied ? 'Đã sao chép!' : 'Chia sẻ'}</span>
        </button>
      </div>
    </div>
  );
}

// ─── Compose Box ─────────────────────────────────────────────────────────────
function ComposeBox({ currentUser, onPost }) {
  const [text, setText]         = useState('');
  const [urgent, setUrgent]     = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]       = useState('');
  const textareaRef = useRef(null);

  const role       = currentUser?.role || 'TEACHER';
  const avatarGrad = ROLE_AVATAR[role] || ROLE_AVATAR.TEACHER;
  const authorName = currentUser?.fullName || currentUser?.username || 'Giáo Viên';

  const MAX_CHARS = 1000;
  const remaining = MAX_CHARS - text.length;
  const isOverLimit = remaining < 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim() || submitting || isOverLimit) return;

    setSubmitting(true);
    setError('');
    try {
      await onPost(text.trim(), urgent);
      setText('');
      setUrgent(false);
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    } catch (err) {
      setError(typeof err === 'string' ? err : err?.message || 'Lỗi đăng tin.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleInput = (e) => {
    setText(e.target.value);
    // Auto-expand textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white/[0.04] border border-white/[0.09] rounded-2xl overflow-hidden shadow-sm transition-all focus-within:border-blue-500/40"
    >
      <div className="p-4 flex gap-3">
        {/* Author Avatar */}
        <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${avatarGrad} flex items-center justify-center text-white text-xs font-extrabold shadow-md shrink-0`}>
          {getInitials(authorName)}
        </div>

        {/* Text Area */}
        <textarea
          ref={textareaRef}
          rows={2}
          value={text}
          onChange={handleInput}
          className="w-full bg-transparent text-sm text-gray-100 placeholder-gray-500 focus:outline-none resize-none leading-relaxed overflow-hidden"
          placeholder="Soạn thông báo chính thức hoặc chia sẻ tin tức mới với toàn trường..."
        />
      </div>

      {/* Toolbar + Submit */}
      <div className="px-4 py-3 border-t border-white/[0.06] bg-black/10 flex items-center gap-2">
        {/* Attach image button (UI-only placeholder) */}
        <button
          type="button"
          className="p-1.5 rounded-lg text-gray-400 hover:text-blue-400 hover:bg-blue-500/10 transition-all duration-150 cursor-pointer"
          title="Đính kèm ảnh (coming soon)"
        >
          <ImagePlus className="w-4 h-4" />
        </button>

        {/* Urgent toggle */}
        <button
          type="button"
          onClick={() => setUrgent((u) => !u)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all duration-150 cursor-pointer ${
            urgent
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : 'text-gray-400 hover:text-orange-400 hover:bg-orange-500/10'
          }`}
          title="Đánh dấu thông báo gấp"
        >
          <AlertCircle className="w-3.5 h-3.5" />
          {urgent ? 'Thông báo gấp' : 'Gấp?'}
        </button>

        {/* Char counter */}
        <span className={`text-[11px] font-mono ml-1 ${isOverLimit ? 'text-red-400' : remaining < 50 ? 'text-amber-400' : 'text-gray-400'}`}>
          {remaining}
        </span>

        {/* Error */}
        {error && <span className="text-[11px] text-red-400 truncate max-w-[140px]">{error}</span>}

        {/* Submit */}
        <button
          type="submit"
          disabled={!text.trim() || submitting || isOverLimit}
          className="ml-auto flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold shadow-md shadow-blue-500/25 transition-all duration-150 cursor-pointer"
        >
          {submitting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
          {submitting ? 'Đang đăng...' : 'Đăng Tin'}
        </button>
      </div>
    </form>
  );
}

// ─── SchoolFeed (Main) ────────────────────────────────────────────────────────
export function SchoolFeed({ currentUser, onOpenSearchSchool }) {
  const { tabs } = useRoleAccess(currentUser?.role || 'STUDENT');
  const [activeTab, setActiveTab] = useState(tabs[0]?.id || 'feed');
  const [posts, setPosts]         = useState([]);
  const [loading, setLoading]     = useState(false);

  const schoolId = currentUser?.school_id || currentUser?.schoolId;
  const hasSchool = !!schoolId;
  const canPost = ['TEACHER','SCHOOL_ADMIN','HEADMASTER','ADMIN','PLATFORM_ADMIN','INSPECTOR'].includes(currentUser?.role);

  const fetchPosts = async () => {
    if (!schoolId) return;
    setLoading(true);
    try {
      const res = await postService.getPosts(schoolId);
      if (res?.status === 'success' && Array.isArray(res.data)) setPosts(res.data);
    } catch (err) {
      console.error('Error fetching posts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPosts(); }, [schoolId]);

  const handlePost = async (contentOrObj, urgentFlag) => {
    let content = '';
    let urgent = false;
    if (typeof contentOrObj === 'object' && contentOrObj !== null) {
      content = contentOrObj.content || '';
      urgent = !!contentOrObj.isUrgent;
    } else {
      content = String(contentOrObj || '');
      urgent = !!urgentFlag;
    }

    content = content.trim();
    if (!content) return;

    const finalContent = urgent && !content.startsWith('🚨 [KHẨN CẤP]')
      ? `🚨 [KHẨN CẤP] ${content}`
      : content;

    const res = await postService.createPost(finalContent, schoolId, { urgent });
    if (res?.status === 'success' && res.data) {
      setPosts((prev) => [res.data, ...prev]);
    } else {
      throw new Error(res?.detail || res?.message || 'Không thể đăng bài.');
    }
  };

  const handleLike = async (postId) => {
    setPosts((prev) => prev.map((p) => {
      if (p.id !== postId) return p;
      const liked = !p.liked;
      return { ...p, liked, likes: liked ? (p.likes || 0) + 1 : Math.max(0, (p.likes || 0) - 1) };
    }));
    try {
      const res = await postService.toggleLike(postId);
      if (res?.status === 'success') {
        setPosts((prev) => prev.map((p) => p.id === postId ? { ...p, liked: res.liked, likes: res.likes } : p));
      }
    } catch {}
  };

  const handleDelete = async (postId) => {
    if (!window.confirm('Xóa bài đăng này?')) return;
    try {
      await postService.deletePost(postId);
      setPosts((prev) => prev.filter((p) => p.id !== postId));
    } catch (err) {
      alert(err.message || 'Lỗi khi xóa bài viết.');
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-5">

      {/* Onboarding Banner */}
      {!hasSchool && (
        <div className="relative overflow-hidden bg-gradient-to-r from-blue-900/30 via-indigo-900/20 to-purple-900/30 border border-blue-500/20 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(59,130,246,0.08),transparent_70%)] pointer-events-none" />
          <div className="relative space-y-1.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/20 border border-blue-500/20 text-blue-400 text-[11px] font-bold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Bước tiếp theo</span>
            </span>
            <h3 className="text-sm font-bold text-white">Bạn chưa tham gia trường học nào</h3>
            <p className="text-xs text-gray-300 max-w-sm leading-relaxed">
              Tìm kiếm và chọn ngôi trường của bạn để xem bảng tin, thời khóa biểu và đồng bộ điểm danh AI Camera.
            </p>
          </div>
          <button
            onClick={onOpenSearchSchool}
            className="relative shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-lg shadow-blue-500/25 transition-all duration-150 cursor-pointer"
          >
            <School className="w-3.5 h-3.5" />
            Tìm &amp; Tham Gia Trường
          </button>
        </div>
      )}

      {/* Pending Review Banner */}
      {hasSchool && currentUser?.verified_status === 'PENDING_REVIEW' && (
        <div className="relative overflow-hidden bg-gradient-to-r from-amber-900/30 via-yellow-900/20 to-orange-900/30 border border-yellow-500/30 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 text-[11px] font-bold">
              <Clock className="w-3.5 h-3.5" />
              <span>Đang Chờ Ban Giám Hiệu Phê Duyệt</span>
            </span>
            <h3 className="text-sm font-bold text-white">Yêu cầu gia nhập trường đang được xử lý</h3>
            <p className="text-xs text-gray-300 max-w-md leading-relaxed">
              Mã định danh tự động: <code className="text-yellow-400 font-mono font-semibold">{currentUser?.user_code || currentUser?.student_code || `ID-${currentUser?.id}`}</code>. Sau khi Hiệu trưởng phê duyệt, tài khoản của bạn sẽ được kích hoạt chính thức.
            </p>
          </div>
          {onOpenSearchSchool && (
            <button
              onClick={onOpenSearchSchool}
              className="shrink-0 text-xs text-blue-400 hover:text-blue-300 underline cursor-pointer"
            >
              Chọn trường khác
            </button>
          )}
        </div>
      )}

      {/* Role Navigation Tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-150 whitespace-nowrap shrink-0 cursor-pointer ${
                active
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-500/25'
                  : 'bg-white/[0.04] hover:bg-white/[0.08] text-gray-300 hover:text-white'
              }`}
            >
              {Icon && <Icon className="w-3.5 h-3.5" />}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ── Approvals Tab ── */}
      {activeTab === 'approvals' && (
        <AdminPendingRequests schoolId={schoolId} />
      )}

      {/* ── Members Management Tab ── */}
      {activeTab === 'members' && (
        <SchoolMemberManagement schoolId={schoolId} />
      )}

      {/* ── Feed Tab ── */}
      {activeTab === 'feed' && (
        <div className="space-y-4">
          {/* Compose Box */}
          {canPost && <ComposeBox currentUser={currentUser} onPost={handlePost} />}

          {/* Posts */}
          {loading ? (
            <div className="space-y-4">
              <PostSkeleton />
              <PostSkeleton />
              <PostSkeleton />
            </div>
          ) : posts.length === 0 ? (
            <EmptyFeedState canPost={canPost} />
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <PostCard
                  key={post.id}
                  post={post}
                  currentUser={currentUser}
                  onLike={handleLike}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Attendance History Tab — Student QR Card ── */}
      {activeTab === 'attendance_history' && (
        <StudentQRCard currentUser={currentUser} />
      )}

      {/* ── Child Attendance Tab — Parent Timeline ── */}
      {activeTab === 'child_attendance' && (
        <ParentChildTimeline currentUser={currentUser} />
      )}

      {/* ── Classes & Discussion Tab — Class Hub ── */}
      {activeTab === 'classes' && (
        <ClassHub currentUser={currentUser} />
      )}

      {/* ── Honor Board Tab ── */}
      {activeTab === 'honor' && (
        <HonorBoard currentUser={currentUser} />
      )}

      {/* ── Fallback for other tabs ── */}
      {!['approvals','members','feed','attendance_history','child_attendance','classes','honor'].includes(activeTab) && (
        <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto">
            <Calendar className="w-7 h-7 text-indigo-400" />
          </div>
          <div className="space-y-1.5">
            <h4 className="text-base font-bold text-white">
              {tabs.find((t) => t.id === activeTab)?.label || activeTab}
            </h4>
            <p className="text-xs text-gray-300 max-w-xs mx-auto leading-relaxed">
              Tính năng này được quản lý đầy đủ trên trang Dashboard Chuyên Sâu theo phân quyền của bạn.
            </p>
          </div>
          <a
            href={`/app/index.html?school_id=${schoolId || 1}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-indigo-500/25 transition cursor-pointer"
          >
            Mở Dashboard ↗
          </a>
        </div>
      )}
    </div>
  );
}
