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
  const isAdminRoute = window.location.pathname
    .replace(/\/+$/, '')
    .endsWith('/admin')
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

  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...options,
      headers,
    }
  )

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
