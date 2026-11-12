/**
 * src/features/classes/ClassHub.jsx
 * Không gian Lớp Học & Diễn Đàn Thảo Luận Số cho Học Sinh & Giáo Viên
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Users, MessageSquare, Award, BookOpen, Send, Heart,
  Share2, MessageCircle, Sparkles, AlertCircle, CheckCircle2,
  Copy, ShieldCheck, UserCheck, Search, Loader2, Plus,
  ChevronRight, Calendar, User, HelpCircle, FileText
} from 'lucide-react';
import { classService } from '../../services/classService';
import { postService } from '../../services/postService';

// ─── Helpers ─────────────────────────────────────────────────────────────────
function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || '?';
}

const CATEGORY_TAGS = {
  DISCUSSION: { label: 'Thảo luận', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/30', icon: MessageSquare },
  QNA:        { label: 'Hỏi bài STEM', cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: HelpCircle },
  HOMEWORK:   { label: 'Bài tập', cls: 'bg-purple-500/15 text-purple-400 border-purple-500/30', icon: FileText },
  MATERIAL:   { label: 'Tài liệu', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', icon: BookOpen },
};

// ─── Comment Item Component ──────────────────────────────────────────────────
function CommentItem({ comment, currentUser, onDelete }) {
  const isAuthor = comment.userId === (currentUser?.id || currentUser?.user_id);
  const canDelete = isAuthor || ['TEACHER', 'HEADMASTER', 'ADMIN'].includes(currentUser?.role);

  return (
    <div className="flex gap-2.5 text-xs group">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shrink-0 text-[10px]">
        {comment.avatarText || getInitials(comment.author)}
      </div>
      <div className="flex-1 bg-white/[0.04] border border-white/[0.06] rounded-xl p-2.5 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-white">{comment.author}</span>
            {comment.authorRole === 'TEACHER' && (
              <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                GVCN
              </span>
            )}
            <span className="text-gray-500 text-[10px]">{comment.timeText}</span>
          </div>
          {canDelete && (
            <button
              onClick={() => onDelete(comment.id)}
              className="text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition p-0.5 cursor-pointer"
              title="Xóa bình luận"
            >
              ✕
            </button>
          )}
        </div>
        <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">{comment.content}</p>
      </div>
    </div>
  );
}

// ─── Class Discussion Card ───────────────────────────────────────────────────
function ClassPostCard({ post, currentUser, onLike, onDelete }) {
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [copied, setCopied] = useState(false);

  const categoryConf = CATEGORY_TAGS[post.category] || CATEGORY_TAGS.DISCUSSION;
  const isTeacher = post.roleTag === 'TEACHER';
  const canDelete =
    ['ADMIN', 'HEADMASTER', 'TEACHER'].includes(currentUser?.role) ||
    post.authorId === (currentUser?.id || currentUser?.user_id);

  const loadComments = async () => {
    if (!showComments) {
      setLoadingComments(true);
      try {
        const res = await classService.getComments(post.id);
        if (res?.status === 'success' && Array.isArray(res.data)) {
          setComments(res.data);
        }
      } catch (err) {
        console.error('Failed to load comments:', err);
      } finally {
        setLoadingComments(false);
      }
    }
    setShowComments(!showComments);
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim() || submittingComment) return;

    setSubmittingComment(true);
    try {
      const res = await classService.addComment(post.id, commentText.trim());
      if (res?.status === 'success' && res.data) {
        setComments((prev) => [...prev, res.data]);
        setCommentText('');
        post.commentsCount = (post.commentsCount || 0) + 1;
      }
    } catch (err) {
      alert(err.message || 'Không thể gửi bình luận.');
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await classService.deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      post.commentsCount = Math.max(0, (post.commentsCount || 1) - 1);
    } catch (err) {
      alert(err.message || 'Lỗi khi xóa bình luận.');
    }
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white/[0.03] hover:bg-white/[0.04] border border-white/[0.07] rounded-2xl overflow-hidden transition-all duration-200">
      <div className="p-4 sm:p-5 space-y-3">
        {/* Author Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${isTeacher ? 'from-purple-500 to-indigo-600' : 'from-blue-500 to-cyan-600'} flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-md`}>
              {post.avatarText || getInitials(post.author)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-white">{post.author}</h4>
                {isTeacher ? (
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Giáo Viên
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    Học Sinh
                  </span>
                )}
              </div>
              <p className="text-[11px] text-gray-400">{post.timeText}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1 ${categoryConf.cls}`}>
              {categoryConf.label}
            </span>
            {canDelete && (
              <button
                onClick={() => onDelete(post.id)}
                className="p-1 text-gray-400 hover:text-red-400 transition cursor-pointer"
                title="Xóa bài viết"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">{post.content}</p>
      </div>

      {/* Action Footer */}
      <div className="px-4 sm:px-5 py-2.5 bg-black/20 border-t border-white/[0.05] flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {/* Like Button */}
          <button
            onClick={() => onLike(post.id)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              post.liked
                ? 'text-rose-400 bg-rose-500/10'
                : 'text-gray-400 hover:text-rose-400 hover:bg-rose-500/10'
            }`}
          >
            <Heart className={`w-3.5 h-3.5 ${post.liked ? 'fill-rose-400' : ''}`} />
            <span>{post.likes || 0}</span>
          </button>

          {/* Comment Toggle Button */}
          <button
            onClick={loadComments}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer ${
              showComments
                ? 'text-blue-400 bg-blue-500/10'
                : 'text-gray-400 hover:text-blue-400 hover:bg-blue-500/10'
            }`}
          >
            <MessageCircle className="w-3.5 h-3.5" />
            <span>{post.commentsCount || 0} bình luận</span>
          </button>
        </div>

        <button
          onClick={handleShare}
          className="flex items-center gap-1 text-gray-400 hover:text-white px-2 py-1 rounded transition cursor-pointer"
        >
          <Share2 className="w-3.5 h-3.5" />
          <span>{copied ? 'Đã chép!' : 'Chia sẻ'}</span>
        </button>
      </div>

      {/* Comments Section */}
      {showComments && (
        <div className="px-4 sm:px-5 py-3 border-t border-white/[0.05] bg-black/30 space-y-3">
          {/* Comment List */}
          {loadingComments ? (
            <div className="py-4 text-center text-gray-400 text-xs flex items-center justify-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
              Đang tải trao đổi...
            </div>
          ) : comments.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-2">Chưa có bình luận nào. Hãy gửi phản hồi đầu tiên!</p>
          ) : (
            <div className="space-y-2.5 pt-1">
              {comments.map((c) => (
                <CommentItem
                  key={c.id}
                  comment={c}
                  currentUser={currentUser}
                  onDelete={handleDeleteComment}
                />
              ))}
            </div>
          )}

          {/* Input Box */}
          <form onSubmit={handleAddComment} className="flex gap-2 pt-2 border-t border-white/[0.05]">
            <input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Viết phản hồi hoặc câu trả lời..."
              className="flex-1 bg-white/[0.05] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
            />
            <button
              type="submit"
              disabled={!commentText.trim() || submittingComment}
              className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white font-semibold text-xs flex items-center gap-1 shadow transition cursor-pointer"
            >
              {submittingComment ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
              Gửi
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

// ─── Main ClassHub Component ─────────────────────────────────────────────────
export function ClassHub({ currentUser }) {
  const schoolId = currentUser?.school_id || currentUser?.schoolId;

  const [loading, setLoading] = useState(true);
  const [hasClass, setHasClass] = useState(false);
  const [classData, setClassData] = useState(null);
  const [classmates, setClassmates] = useState([]);
  const [latestScore, setLatestScore] = useState(null);

  // Sub-tabs
  const [subTab, setSubTab] = useState('discussions'); // 'discussions' | 'classmates' | 'discipline'

  // Invite code join state
  const [inviteCode, setInviteCode] = useState('');
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState('');
  const [copiedCode, setCopiedCode] = useState(false);

  // Posts State
  const [posts, setPosts] = useState([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('');

  // Compose State
  const [composeText, setComposeText] = useState('');
  const [composeCategory, setComposeCategory] = useState('DISCUSSION');
  const [posting, setPosting] = useState(false);

  // Search classmates
  const [classmateSearch, setClassmateSearch] = useState('');

  // Fetch Class Info
  const fetchMyClass = async () => {
    if (!schoolId) return;
    setLoading(true);
    try {
      const res = await classService.getMyClass(schoolId);
      if (res?.has_class) {
        setHasClass(true);
        setClassData(res.class);
        setClassmates(res.classmates || []);
        setLatestScore(res.latest_score || null);
        // Load discussions for this class
        loadPosts(res.class.id, selectedCategory);
      } else {
        setHasClass(false);
      }
    } catch (err) {
      console.error('Failed to fetch my class:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPosts = async (classId, cat = '') => {
    if (!classId) return;
    setLoadingPosts(true);
    try {
      const res = await classService.getClassPosts(schoolId, classId, cat);
      if (res?.status === 'success' && Array.isArray(res.data)) {
        setPosts(res.data);
      }
    } catch (err) {
      console.error('Failed to fetch class posts:', err);
    } finally {
      setLoadingPosts(false);
    }
  };

  useEffect(() => {
    fetchMyClass();
  }, [schoolId]);

  // Filter posts when category tab changes
  const handleCategoryChange = (cat) => {
    setSelectedCategory(cat);
    if (classData?.id) {
      loadPosts(classData.id, cat);
    }
  };

  // Handle Join Class
  const handleJoinClass = async (e) => {
    e.preventDefault();
    if (!inviteCode.trim() || joining) return;

    setJoining(true);
    setJoinError('');
    try {
      const res = await classService.joinClass(schoolId, inviteCode.trim());
      if (res?.status === 'success') {
        setInviteCode('');
        await fetchMyClass();
      } else {
        setJoinError(res?.message || 'Không thể tham gia lớp.');
      }
    } catch (err) {
      setJoinError(err?.message || 'Mã mời lớp không hợp lệ.');
    } finally {
      setJoining(false);
    }
  };

  // Handle Post Creation
  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!composeText.trim() || posting || !classData?.id) return;

    setPosting(true);
    try {
      const res = await classService.createClassPost(schoolId, classData.id, composeText.trim(), composeCategory);
      if (res?.status === 'success' && res.data) {
        setPosts((prev) => [res.data, ...prev]);
        setComposeText('');
      }
    } catch (err) {
      alert(err.message || 'Lỗi khi gửi thảo luận.');
    } finally {
      setPosting(false);
    }
  };

  const handleLikePost = async (postId) => {
    setPosts((prev) =>
      prev.map((p) => {
        if (p.id !== postId) return p;
        const liked = !p.liked;
        return {
          ...p,
          liked,
          likes: liked ? (p.likes || 0) + 1 : Math.max(0, (p.likes || 0) - 1),
        };
      })
    );
    try {
      const res = await postService.toggleLike(postId);
      if (res?.status === 'success') {
        setPosts((prev) =>
          prev.map((p) => (p.id === postId ? { ...p, liked: res.liked, likes: res.likes } : p))
        );
      }
    } catch {}
  };

  const handleDeletePost = async (postId) => {
    if (!window.confirm('Bạn có chắc muốn xóa bài thảo luận này?')) return;
    try {
      await postService.deletePost(postId);
      setPosts((prev) => prev.filter((p) => p.id !== postId));
    } catch (err) {
      alert(err.message || 'Không thể xóa bài viết.');
    }
  };

  const copyInvite = () => {
    if (classData?.invite_code) {
      navigator.clipboard?.writeText(classData.invite_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  // Filtered Classmates
  const filteredClassmates = classmates.filter((s) => {
    const q = classmateSearch.toLowerCase();
    return s.full_name?.toLowerCase().includes(q) || s.student_code?.toLowerCase().includes(q);
  });

  if (loading) {
    return (
      <div className="py-16 text-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto" />
        <p className="text-sm text-gray-400">Đang tải thông tin lớp học...</p>
      </div>
    );
  }

  // ─── Case 1: Học sinh chưa tham gia lớp ─────────────────────────────────────
  if (!hasClass) {
    return (
      <div className="bg-white/[0.03] border border-white/[0.08] rounded-3xl p-6 sm:p-10 text-center max-w-lg mx-auto space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center mx-auto text-blue-400 shadow-inner">
          <Users className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h3 className="text-lg sm:text-xl font-bold text-white">Bạn chưa tham gia lớp học nào</h3>
          <p className="text-xs sm:text-sm text-gray-300 leading-relaxed max-w-sm mx-auto">
            Nhập Mã Mời Lớp do Giáo Viên Chủ Nhiệm hoặc Ban Giám Hiệu cung cấp để mở không gian lớp học số và tham gia thảo luận.
          </p>
        </div>

        <form onSubmit={handleJoinClass} className="space-y-3 max-w-sm mx-auto">
          <div className="relative">
            <input
              type="text"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
              placeholder="VD: INVITE_10A1_XXXX"
              className="w-full bg-white/[0.06] border border-white/[0.12] rounded-xl px-4 py-3 text-center text-sm font-mono tracking-widest text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/60 uppercase"
            />
          </div>

          {joinError && (
            <p className="text-xs text-red-400 flex items-center justify-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              {joinError}
            </p>
          )}

          <button
            type="submit"
            disabled={!inviteCode.trim() || joining}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 text-white font-bold text-xs shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            {joining ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <UserCheck className="w-4 h-4" />
            )}
            <span>Tham Gia Lớp Ngay</span>
          </button>
        </form>

        <div className="pt-2 border-t border-white/[0.05] text-[11px] text-gray-400">
          Chưa có mã lớp? Hãy liên hệ với Giáo viên chủ nhiệm để nhận mã mời.
        </div>
      </div>
    );
  }

  // ─── Case 2: Đã có lớp ─────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Class Hub Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-blue-950/40 border border-white/[0.09] p-5 sm:p-7 shadow-xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-2">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Khối {classData.grade_level} · Năm học {classData.academic_year}
              </span>
              {classData.invite_code && (
                <button
                  onClick={copyInvite}
                  className="px-2.5 py-1 rounded-full text-[11px] font-mono bg-white/[0.05] hover:bg-white/[0.1] text-gray-300 border border-white/[0.1] flex items-center gap-1.5 transition cursor-pointer"
                  title="Sao chép mã mời lớp"
                >
                  <Copy className="w-3 h-3 text-gray-400" />
                  <span>{copiedCode ? 'Đã sao chép!' : classData.invite_code}</span>
                </button>
              )}
            </div>

            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2">
              <span>{classData.name}</span>
              <Sparkles className="w-5 h-5 text-amber-400 shrink-0" />
            </h2>

            <p className="text-xs sm:text-sm text-gray-300 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-purple-400" />
              <span>GVCN: <strong className="text-white">{classData.teacher_name}</strong></span>
              {classData.teacher_phone && (
                <span className="text-gray-400">· ĐT: {classData.teacher_phone}</span>
              )}
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 sm:gap-3 shrink-0">
            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-3 text-center">
              <span className="text-[11px] text-gray-400 font-medium">Sĩ Số Lớp</span>
              <div className="text-lg sm:text-xl font-extrabold text-white mt-0.5">
                {classData.student_count || classmates.length}
              </div>
            </div>

            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-3 text-center">
              <span className="text-[11px] text-gray-400 font-medium">Thảo Luận</span>
              <div className="text-lg sm:text-xl font-extrabold text-blue-400 mt-0.5">
                {posts.length}
              </div>
            </div>

            <div className="col-span-2 sm:col-span-1 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-3 text-center">
              <span className="text-[11px] text-gray-400 font-medium">Thi Đua Tuần</span>
              <div className="text-lg sm:text-xl font-extrabold text-emerald-400 mt-0.5">
                {latestScore?.total_points != null ? `${latestScore.total_points}đ` : '100đ'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Internal Sub-navigation Tabs */}
      <div className="flex border-b border-white/[0.08] gap-2 sm:gap-4 overflow-x-auto scrollbar-none pb-1">
        <button
          onClick={() => setSubTab('discussions')}
          className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            subTab === 'discussions'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Thảo Luận &amp; Hỏi Đáp ({posts.length})</span>
        </button>

        <button
          onClick={() => setSubTab('classmates')}
          className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            subTab === 'classmates'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Thành Viên Lớp ({classmates.length})</span>
        </button>

        <button
          onClick={() => setSubTab('discipline')}
          className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            subTab === 'discipline'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Award className="w-4 h-4" />
          <span>Nề Nếp &amp; Thi Đua</span>
        </button>
      </div>

      {/* ── SUB-TAB 1: THẢO LUẬN & HỎI ĐÁP ── */}
      {subTab === 'discussions' && (
        <div className="space-y-5">
          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            <button
              onClick={() => handleCategoryChange('')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer whitespace-nowrap ${
                selectedCategory === ''
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-500/25'
                  : 'bg-white/[0.04] text-gray-400 hover:text-white'
              }`}
            >
              Tất Cả
            </button>
            {Object.entries(CATEGORY_TAGS).map(([key, conf]) => (
              <button
                key={key}
                onClick={() => handleCategoryChange(key)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                  selectedCategory === key
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/25'
                    : 'bg-white/[0.04] text-gray-400 hover:text-white'
                }`}
              >
                <conf.icon className="w-3.5 h-3.5" />
                <span>{conf.label}</span>
              </button>
            ))}
          </div>

          {/* Discussion Compose Box */}
          <form
            onSubmit={handleCreatePost}
            className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-4 space-y-3 focus-within:border-blue-500/40 transition"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
                Soạn câu hỏi hoặc bài thảo luận
              </span>

              {/* Tag selection */}
              <div className="flex items-center gap-1.5">
                {Object.entries(CATEGORY_TAGS).map(([key, conf]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setComposeCategory(key)}
                    className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold transition cursor-pointer ${
                      composeCategory === key
                        ? `${conf.cls} border font-bold`
                        : 'text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    {conf.label}
                  </button>
                ))}
              </div>
            </div>

            <textarea
              rows={2}
              value={composeText}
              onChange={(e) => setComposeText(e.target.value)}
              placeholder="Đặt câu hỏi về bài tập STEM, trao đổi bài học hoặc chia sẻ tài liệu với các bạn trong lớp..."
              className="w-full bg-transparent text-xs sm:text-sm text-gray-100 placeholder-gray-500 focus:outline-none resize-none leading-relaxed"
            />

            <div className="flex items-center justify-between pt-2 border-t border-white/[0.05]">
              <span className="text-[11px] text-gray-500">Mọi người trong lớp đều có thể xem và phản hồi</span>
              <button
                type="submit"
                disabled={!composeText.trim() || posting}
                className="px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white font-bold text-xs shadow-md shadow-blue-500/25 flex items-center gap-1.5 transition cursor-pointer"
              >
                {posting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>Đăng Thảo Luận</span>
              </button>
            </div>
          </form>

          {/* Posts List */}
          {loadingPosts ? (
            <div className="py-10 text-center space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
              <p className="text-xs text-gray-400">Đang tải bài thảo luận của lớp...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-10 text-center space-y-3">
              <MessageSquare className="w-10 h-10 text-gray-500 mx-auto opacity-40" />
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-white">Chưa có bài thảo luận nào</h4>
                <p className="text-xs text-gray-400 max-w-xs mx-auto">
                  Hãy là người đầu tiên đặt câu hỏi hoặc chia sẻ tài liệu học tập với lớp!
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <ClassPostCard
                  key={post.id}
                  post={post}
                  currentUser={currentUser}
                  onLike={handleLikePost}
                  onDelete={handleDeletePost}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── SUB-TAB 2: THÀNH VIÊN LỚP ── */}
      {subTab === 'classmates' && (
        <div className="space-y-4">
          {/* Search box */}
          <div className="relative max-w-sm">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={classmateSearch}
              onChange={(e) => setClassmateSearch(e.target.value)}
              placeholder="Tìm bạn cùng lớp theo tên, mã HS..."
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          {/* Classmates Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {filteredClassmates.map((s, idx) => (
              <div
                key={s.id || idx}
                className="bg-white/[0.03] hover:bg-white/[0.05] border border-white/[0.07] rounded-2xl p-3.5 flex items-center gap-3 transition"
              >
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow">
                  {getInitials(s.full_name)}
                </div>
                <div className="min-w-0 flex-1">
                  <h4 className="text-xs font-bold text-white truncate">{s.full_name}</h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-blue-400 font-mono">{s.student_code}</span>
                    {s.current_points != null && (
                      <span className="text-[10px] text-emerald-400 font-semibold">
                        ⭐ {s.current_points}đ
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredClassmates.length === 0 && (
            <p className="text-center text-xs text-gray-400 py-6">Không tìm thấy thành viên phù hợp.</p>
          )}
        </div>
      )}

      {/* ── SUB-TAB 3: NỀ NẾP & THI ĐUA ── */}
      {subTab === 'discipline' && (
        <div className="space-y-4">
          <div className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white">Điểm Thi Đua Tuần Hiện Tại</h3>
                <p className="text-xs text-gray-400">Được tổng hợp từ hệ thống AI Camera &amp; Ban Giám Thị</p>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                {latestScore?.total_points != null ? `${latestScore.total_points} Điểm` : '100 Điểm'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3 text-center">
                <span className="text-[11px] text-gray-400">Chuyên Cần</span>
                <div className="text-base font-bold text-white mt-1">
                  {latestScore?.attendance_score != null ? latestScore.attendance_score : '100'}đ
                </div>
              </div>
              <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3 text-center">
                <span className="text-[11px] text-gray-400">Đồng Phục</span>
                <div className="text-base font-bold text-white mt-1">
                  {latestScore?.uniform_score != null ? latestScore.uniform_score : '100'}đ
                </div>
              </div>
              <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3 text-center">
                <span className="text-[11px] text-gray-400">Kỷ Luật &amp; Nề Nếp</span>
                <div className="text-base font-bold text-white mt-1">
                  {latestScore?.discipline_score != null ? latestScore.discipline_score : '100'}đ
                </div>
              </div>
              <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3 text-center">
                <span className="text-[11px] text-gray-400">Điểm Thưởng</span>
                <div className="text-base font-bold text-emerald-400 mt-1">
                  +{latestScore?.bonus_points != null ? latestScore.bonus_points : '0'}đ
                </div>
              </div>
            </div>

            {latestScore?.inspector_notes && (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-xs text-amber-300">
                <strong>Nhận xét từ Giám Thị:</strong> {latestScore.inspector_notes}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
