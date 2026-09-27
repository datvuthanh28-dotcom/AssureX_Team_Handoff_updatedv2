const API_BASE = `http://${window.location.hostname}:8000`
const CUSTOMER_TOKEN_KEY = 'assurex_customer_token'
const ADMIN_TOKEN_KEY = 'assurex_admin_token'


export async function api(
  path,
  options = {},
) {
  const isFormData =
    options.body instanceof FormData

  const headers = {
    ...(options.headers || {}),
  }
  const pathname = window.location.pathname.replace(/\/+$/, '') || '/'
  const isAdminRoute = pathname === '/admin' || pathname.startsWith('/admin/') || pathname.endsWith('/admin')
  const token = localStorage.getItem(
    isAdminRoute ? ADMIN_TOKEN_KEY : CUSTOMER_TOKEN_KEY
  )
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }

  if (
    options.body &&
    !isFormData &&
    !headers['Content-Type']
  ) {
    headers['Content-Type'] =
      'application/json'
  }

  let response
  try {
    response = await fetch(
      `${API_BASE}${path}`,
      {
        ...options,
        headers,
      }
    )
  } catch (networkError) {
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      try {
        response = await fetch(
          `http://localhost:8000${path}`,
          {
            ...options,
            headers,
          }
        )
      } catch {
        throw networkError
      }
    } else {
      throw networkError
    }
  }

  let data = null

  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ||
      `Request failed: ${response.status}`
    )
  }

  return data
}
