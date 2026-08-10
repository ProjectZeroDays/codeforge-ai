import { NextResponse } from 'next/server'

export const dynamic = 'force-static'

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  try {
    const res = await fetch(`${backendUrl}/health`, {
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) {
      return NextResponse.json(
        { status: 'unhealthy', upstream: res.status },
        { status: 503 }
      )
    }
    const data = await res.json()
    return NextResponse.json(data, { status: 200 })
  } catch (err) {
    return NextResponse.json(
      { status: 'unhealthy', error: 'backend unreachable' },
      { status: 503 }
    )
  }
}