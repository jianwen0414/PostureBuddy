'use client'

import { useDashboardStore } from '@/store/useDashboardStore'

export default function ConversationPanel() {
  const conversation = useDashboardStore((s) => s.conversation)

  return (
    <section className="flex h-full min-h-[240px] flex-col overflow-hidden rounded-xl border border-slate-700/50 bg-slate-800/20 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-700/50 px-4 py-2">
        <span className="text-[10px] font-display font-semibold uppercase tracking-widest text-slate-500">
          Conversation
        </span>
        {conversation.length > 0 && (
          <span className="rounded-full bg-slate-700/50 px-2 py-0.5 text-[10px] text-slate-300">
            {conversation.length}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {conversation.length === 0 ? (
          <div className="flex h-full min-h-[180px] items-center justify-center text-center">
            <div>
              <p className="text-sm text-slate-500">No conversation yet</p>
              <p className="mt-1 text-xs text-slate-600">The robot&apos;s prompts will appear here.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {conversation.map((entry, index) => {
              const isUser = entry.startsWith('User:')
              return (
                <div
                  key={`${entry}-${index}`}
                  className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm ${
                    isUser
                      ? 'ml-auto bg-cyan-500/15 text-cyan-50'
                      : 'bg-slate-700/50 text-slate-100'
                  }`}
                >
                  <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    {isUser ? 'You' : 'Robot'}
                  </span>
                  <span className="mt-1 block whitespace-pre-wrap">{entry.replace(/^User:\s?|^Robot:\s?/, '')}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
