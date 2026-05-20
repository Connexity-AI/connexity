import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export const GET = async (): Promise<Response> =>
  NextResponse.json({ status: 'ok' }, { status: 200 });
