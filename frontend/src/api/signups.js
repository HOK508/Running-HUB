// 报名模块接口
import request from './request'

export function signup(activityId) {
  return request.post(`/activities/${activityId}/signup`)
}

export function cancelSignup(activityId, data) {
  return request.post(`/activities/${activityId}/signup/cancel`, data)
}

export function allSignups() {
  return request.get('/signups/all')
}

export function listCancellations() {
  return request.get('/signups/cancellations')
}

export function noShowRecords() {
  return request.get('/signups/no-shows')
}

export function markMalicious(id, data) {
  return request.put(`/signups/cancellations/${id}/malicious`, data)
}

export function reviewSignup(id, data) {
  return request.put(`/signups/${id}/review`, data)
}

export function listSignups(activityId) {
  return request.get(`/activities/${activityId}/signups`)
}

export function mySignups() {
  return request.get('/signups/mine')
}

export function pendingSignups() {
  return request.get('/signups/pending')
}
