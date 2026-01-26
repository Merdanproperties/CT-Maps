import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { propertyApi, Comment } from '../api/client'
import { MessageSquare, Send, Loader2, Edit2, X, Check } from 'lucide-react'
import './PropertyComments.css'

interface PropertyCommentsProps {
  propertyId: number
}

export default function PropertyComments({ propertyId }: PropertyCommentsProps) {
  const [commentText, setCommentText] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const queryClient = useQueryClient()

  // Fetch comments
  const { data: comments = [], isLoading } = useQuery({
    queryKey: ['property-comments', propertyId],
    queryFn: () => propertyApi.getPropertyComments(propertyId),
    enabled: !!propertyId,
  })

  // Create comment mutation
  const createCommentMutation = useMutation({
    mutationFn: (comment: string) => propertyApi.createPropertyComment(propertyId, comment),
    onSuccess: () => {
      // Clear form
      setCommentText('')
      // Invalidate and refetch comments
      queryClient.invalidateQueries({ queryKey: ['property-comments', propertyId] })
    },
    onError: (error: any) => {
      console.error('Error creating comment:', error)
      alert('Failed to add comment. Please try again.')
    },
  })

  // Update comment mutation
  const updateCommentMutation = useMutation({
    mutationFn: ({ commentId, comment }: { commentId: number; comment: string }) =>
      propertyApi.updatePropertyComment(propertyId, commentId, comment),
    onSuccess: () => {
      setEditingId(null)
      setEditText('')
      queryClient.invalidateQueries({ queryKey: ['property-comments', propertyId] })
    },
    onError: (error: any) => {
      console.error('Error updating comment:', error)
      alert('Failed to update comment. Please try again.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (commentText.trim()) {
      createCommentMutation.mutate(commentText.trim())
    }
  }

  const handleStartEdit = (comment: Comment) => {
    setEditingId(comment.id)
    setEditText(comment.comment)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditText('')
  }

  const handleSaveEdit = () => {
    if (editingId && editText.trim()) {
      updateCommentMutation.mutate({ commentId: editingId, comment: editText.trim() })
    }
  }

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) {
      return 'Just now'
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
    } else {
      // Format as "Jan 15, 2024 at 2:30 PM"
      const options: Intl.DateTimeFormatOptions = {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      }
      return date.toLocaleString('en-US', options)
    }
  }

  return (
    <div className="property-comments">
      <div className="comments-header">
        <MessageSquare size={20} />
        <h2>Comments</h2>
      </div>

      {isLoading ? (
        <div className="comments-loading">
          <Loader2 size={20} className="spinner" />
          <span>Loading comments...</span>
        </div>
      ) : comments.length === 0 ? (
        <div className="comments-empty">
          <p>No comments yet. Add a comment to track conversations with the property owner.</p>
        </div>
      ) : (
        <div className="comments-list">
          {comments.map((comment: Comment) => (
            <div key={comment.id} className="comment-item">
              {editingId === comment.id ? (
                <div className="comment-edit">
                  <textarea
                    className="comment-edit-input"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    rows={2}
                    disabled={updateCommentMutation.isPending}
                  />
                  <div className="comment-edit-actions">
                    <button
                      className="comment-save-btn"
                      onClick={handleSaveEdit}
                      disabled={!editText.trim() || updateCommentMutation.isPending}
                    >
                      <Check size={14} />
                    </button>
                    <button
                      className="comment-cancel-btn"
                      onClick={handleCancelEdit}
                      disabled={updateCommentMutation.isPending}
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="comment-content">
                    <div className="comment-text">{comment.comment}</div>
                    <div className="comment-timestamp">{formatTimestamp(comment.created_at)}</div>
                  </div>
                  <button
                    className="comment-edit-btn"
                    onClick={() => handleStartEdit(comment)}
                    title="Edit comment"
                  >
                    <Edit2 size={14} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      <form className="comment-form" onSubmit={handleSubmit}>
        <textarea
          className="comment-input"
          placeholder="Add a comment..."
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          rows={2}
          disabled={createCommentMutation.isPending}
        />
        <button
          type="submit"
          className="comment-submit"
          disabled={!commentText.trim() || createCommentMutation.isPending}
        >
          {createCommentMutation.isPending ? (
            <Loader2 size={14} className="spinner" />
          ) : (
            <Send size={14} />
          )}
        </button>
      </form>
    </div>
  )
}
