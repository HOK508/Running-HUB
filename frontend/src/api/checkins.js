// 签到模块接口
import request from './request'

export function checkin(activityId) {
  return request.post(`/activities/${activityId}/checkin`)
}

export function listCheckins(activityId) {
  return request.get(`/activities/${activityId}/checkins`)
}

// 签到清单：已确认报名者 + 是否签到（未签到的排前面）
export function getAttendance(activityId) {
  return request.get(`/activities/${activityId}/attendance`)
}

export function myCheckins() {
  return request.get('/checkins/mine')
}
