// 帖子互动接口（历史活动回顾）
import request from './request'

export function listReviews() {
  return request.get('/reviews')
}

export function publishReview(activityId, data) {
  return request.post(`/activities/${activityId}/review-post`, data)
}

export function likeActivity(id) {
  return request.post(`/activities/${id}/like`)
}

export function unlikeActivity(id) {
  return request.delete(`/activities/${id}/like`)
}

export function listComments(id) {
  return request.get(`/activities/${id}/comments`)
}

export function createComment(id, data) {
  return request.post(`/activities/${id}/comments`, data)
}
