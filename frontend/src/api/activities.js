// 活动模块接口
import request from './request'

export function createActivity(data) {
  return request.post('/activities', data)
}

export function updateActivity(id, data) {
  return request.put(`/activities/${id}`, data)
}

export function listActivities() {
  return request.get('/activities')
}

export function getActivity(id) {
  return request.get(`/activities/${id}`)
}

export function myActivities() {
  return request.get('/activities/mine')
}

export function listAllActivities() {
  return request.get('/activities/all')
}

export function deleteActivity(id) {
  return request.delete(`/activities/${id}`)
}

export function uploadActivityImage(file) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/activities/images', form)
}
