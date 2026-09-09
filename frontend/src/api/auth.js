// 用户模块接口
import request from './request'

export function login(data) {
  return request.post('/users/login', data)
}

export function register(data) {
  return request.post('/users/register', data)
}

export function getMe() {
  return request.get('/users/me')
}

export function updateProfile(data) {
  return request.put('/users/me', data)
}

export function changePassword(data) {
  return request.post('/users/change-password', data)
}
