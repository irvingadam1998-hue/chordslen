import { NextRequest } from 'next/server'
import { proxyBackend } from '@/lib/backend'

export async function GET(_request: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params
  return proxyBackend(`/transcribe/status/${encodeURIComponent(jobId)}`)
}
