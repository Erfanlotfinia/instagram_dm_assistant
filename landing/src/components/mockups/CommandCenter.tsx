import { channels } from '../../content/site';
import { Icon } from '../ui/Icon';
import { ChannelBadge } from './ChannelBadge';
import { ChatBubble } from './ChatBubble';
import { DecisionTrace } from './DecisionTrace';
import { OrderStatusCard } from './OrderStatusCard';
import { ProductCard } from './ProductCard';

const inbox = [
  { name: 'سارا محمدی', channel: 'Instagram', icon: 'Instagram', preview: 'قیمت این چنده؟', active: true, unread: 2 },
  { name: 'رضا کریمی', channel: 'WhatsApp', icon: 'MessageCircle', preview: 'سفارشم کجاست؟', active: false, unread: 0 },
  { name: 'مینا رستمی', channel: 'Telegram', icon: 'Send', preview: 'چکش بوش دارید؟', active: false, unread: 1 },
];

export function CommandCenter() {
  return (
    <div className="glass-strong relative rounded-3xl p-3 sm:p-4">
      {/* Window chrome */}
      <div className="mb-3 flex items-center justify-between px-1">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-modira-cyan/70" />
          <span className="size-2.5 rounded-full bg-modira-teal/70" />
          <span className="size-2.5 rounded-full bg-modira-teal-dark/70" />
        </div>
        <span className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
          <Icon name="LayoutDashboard" size={12} className="text-modira-cyan" />
          Modira Command Center
        </span>
        <div className="flex items-center gap-1">
          {channels.items.slice(0, 5).map((c, i) => (
            <ChannelBadge key={c.name} icon={c.icon} name={c.name} size="sm" active={i === 0} />
          ))}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[0.85fr_1.1fr_0.95fr]">
        {/* Unified inbox */}
        <div className="rounded-2xl border border-border bg-surface p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-fg">
              <Icon name="Inbox" size={14} className="text-modira-cyan" />
              این‌باکس یکپارچه
            </span>
            <span className="ltr rounded-md bg-modira-cyan/15 px-1.5 py-0.5 text-[10px] text-modira-cyan">
              3 active
            </span>
          </div>
          <ul className="space-y-1.5">
            {inbox.map((item) => (
              <li
                key={item.name}
                className={`flex items-center gap-2 rounded-xl p-2 ${
                  item.active ? 'border border-modira-cyan/30 bg-modira-cyan/10' : 'bg-surface-sunken'
                }`}
              >
                <ChannelBadge icon={item.icon} name={item.channel} size="sm" active={item.active} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-fg">{item.name}</p>
                  <p className="truncate text-[11px] text-muted">{item.preview}</p>
                </div>
                {item.unread > 0 ? (
                  <span className="grid size-4 place-items-center rounded-full accent-gradient text-[9px] font-bold text-modira-navy-deep">
                    {item.unread}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>

        {/* Conversation */}
        <div className="flex flex-col gap-2.5 rounded-2xl border border-border bg-surface p-3">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-fg">
              <Icon name="MessagesSquare" size={14} className="text-modira-cyan" />
              مکالمه
            </span>
            <ChannelBadge icon="Instagram" name="Instagram" size="sm" active />
          </div>
          <ChatBubble from="customer" text="قیمت این چنده؟" attachment={{ type: 'post', label: 'پست ارسالی' }} />
          <ChatBubble from="customer" text="همونو می‌خوام" />
          <ProductCard name="کفش رانینگ مدل Aero" price="۲٬۴۵۰٬۰۰۰ تومان" meta="برند Modira Sport" />
          {/* AI suggestion */}
          <div className="rounded-2xl border border-modira-teal/25 bg-modira-teal/10 p-2.5">
            <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-modira-teal">
              <Icon name="Sparkles" size={12} />
              پیشنهاد پاسخ هوشمند
            </div>
            <p className="text-xs leading-relaxed text-fg">
              «این مدل موجود است. لطفاً سایز را بفرمایید تا پیش‌نویس سفارش را آماده کنم.»
            </p>
            <div className="mt-2 flex gap-1.5">
              <span className="rounded-lg accent-gradient px-2 py-1 text-[11px] font-semibold text-modira-navy-deep">
                ارسال
              </span>
              <span className="rounded-lg border border-border bg-surface-sunken px-2 py-1 text-[11px] text-fg">
                ویرایش
              </span>
            </div>
          </div>
        </div>

        {/* Context column: trace + order + handoff */}
        <div className="flex flex-col gap-2.5">
          <DecisionTrace />
          <OrderStatusCard orderId="#۱۰۹۲" />
          <div className="flex items-center gap-2 rounded-2xl border border-modira-cyan/25 bg-modira-cyan/10 p-2.5">
            <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-modira-cyan/20 text-modira-cyan">
              <Icon name="UserCheck" size={16} />
            </span>
            <div>
              <p className="text-[11px] font-semibold text-modira-cyan">آمادهٔ تحویل به انسان</p>
              <p className="text-[10px] text-modira-cyan/70">در صورت تشخیص ریسک، با زمینهٔ کامل</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
