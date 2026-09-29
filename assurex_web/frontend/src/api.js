const CUSTOMER_TOKEN_KEY = 'assurex_customer_token'
const ADMIN_TOKEN_KEY = 'assurex_admin_token'


const CANDIDATE_PORTS = [8000, 8001, 8080, 5000]
let activeBaseUrl = (() => {
  try {
    return localStorage.getItem('assurex_active_api_base') || null
  } catch {
    return null
  }
})()


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
  const isStaffRoute = ['/admin', '/reviewer'].some((route) => pathname === route || pathname.startsWith(`${route}/`) || pathname.endsWith(route))
  const token = localStorage.getItem(
    isStaffRoute ? ADMIN_TOKEN_KEY : CUSTOMER_TOKEN_KEY
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


  const hostnames = [window.location.hostname]
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    hostnames.push('localhost', '127.0.0.1')
  }

  const basesToTry = []
  if (activeBaseUrl) {
    basesToTry.push(activeBaseUrl)
  }
  for (const port of CANDIDATE_PORTS) {
    for (const host of hostnames) {
      const url = `http://${host}:${port}`
      if (!basesToTry.includes(url)) {
        basesToTry.push(url)
      }
    }
  }

  let response = null
  let lastNetworkError = null

  for (const base of basesToTry) {
    try {
      response = await fetch(`${base}${path}`, {
        ...options,
        headers,
      })

      activeBaseUrl = base
      try {
        localStorage.setItem('assurex_active_api_base', base)
      } catch {

      }
      break
    } catch (netErr) {
      lastNetworkError = netErr

    }
  }

  if (!response) {
    throw new Error(
      `Unable to connect to Backend Server (Failed to fetch). Please ensure the backend is running on port 8000 or 8001 (command: uvicorn app.main:app --reload --host 127.0.0.1 --port 8001).`
    )
  }

  let data = null

  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    const detail = data?.detail
    const detailMessage = Array.isArray(detail)
      ? detail
          .map((item) => {
            const location = Array.isArray(item?.loc) ? item.loc.join('.') : ''
            return [location, item?.msg].filter(Boolean).join(': ')
          })
          .filter(Boolean)
          .join('; ')
      : typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : null
    const err = new Error(
      data?.message ||
      detailMessage ||
      `Request failed: ${response.status}`
    )
    err.data = data
    err.errors = data?.errors
    throw err
  }

  return data
}
