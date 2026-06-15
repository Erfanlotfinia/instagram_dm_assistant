import { Icon } from '../ui/Icon';

type Attachment = { type: 'post' | 'story' | 'product' | 'order'; label: string };

type ChatBubbleProps = {
  from: 'customer' | 'modira';
  text: string;
  attachment?: Attachment;
  label?: string;
};

const attachmentIcon: Record<Attachment['type'], string> = {
  post: 'Image',
  story: 'Clapperboard',
  product: 'Package',
  order: 'Receipt',
};

export function ChatBubble({ from, text, attachment, label }: ChatBubbleProps) {
  const isModira = from === 'modira';

  return (
    <div className={`flex w-full ${isModira ? 'justify-start' : 'justify-end'}`}>
      <div className="flex max-w-[88%] flex-col gap-1.5">
        {!isModira ? (
          <span className="text-end text-[11px] text-mist-500">مشتری</span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-medium text-cyan-400">
            <Icon name="Sparkles" size={12} /> Modira
          </span>
        )}

        {attachment ? (
          <div
            className={`flex items-center gap-2 rounded-2xl border border-mist-200/10 bg-white/5 px-3 py-2 text-xs text-mist-200 ${
              isModira ? 'self-start' : 'self-end'
            }`}
          >
            <Icon name={attachmentIcon[attachment.type]} size={14} className="text-cyan-400" />
            <span>{attachment.label}</span>
          </div>
        ) : null}

        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isModira
              ? 'rounded-tr-2xl rounded-tl-sm border border-cyan-400/20 bg-cyan-500/10 text-mist-50'
              : 'rounded-tl-2xl rounded-tr-sm bg-ink-700/70 text-mist-100'
          }`}
        >
          {text}
        </div>

        {label ? (
          <span className="flex items-center gap-1.5 self-start rounded-lg border border-emerald-400/20 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-300">
            <Icon name="Workflow" size={11} />
            {label}
          </span>
        ) : null}
      </div>
    </div>
  );
}
