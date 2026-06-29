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
          <span className="text-end text-[11px] text-subtle">مشتری</span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-medium text-modira-cyan">
            <Icon name="Sparkles" size={12} /> Modira
          </span>
        )}

        {attachment ? (
          <div
            className={`flex items-center gap-2 rounded-2xl border border-border bg-surface-sunken px-3 py-2 text-xs text-fg ${
              isModira ? 'self-start' : 'self-end'
            }`}
          >
            <Icon name={attachmentIcon[attachment.type]} size={14} className="text-modira-cyan" />
            <span>{attachment.label}</span>
          </div>
        ) : null}

        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isModira
              ? 'rounded-tr-2xl rounded-tl-sm border border-modira-cyan/20 bg-modira-cyan/10 text-fg'
              : 'rounded-tl-2xl rounded-tr-sm bg-surface text-fg'
          }`}
        >
          {text}
        </div>

        {label ? (
          <span className="flex items-center gap-1.5 self-start rounded-lg border border-modira-teal/20 bg-modira-teal/10 px-2 py-1 text-[11px] text-modira-teal">
            <Icon name="Workflow" size={11} />
            {label}
          </span>
        ) : null}
      </div>
    </div>
  );
}
