/**
 * Single source of truth for all landing-page copy and CTAs.
 *
 * HOW TO EDIT:
 * - Brand name, slogans and CTA labels/links: `brand`, `cta` and `nav` below.
 * - Section text: each section has its own typed object.
 * - Icon names map to lucide-react icons (https://lucide.dev/icons).
 *
 * Keep `icon` values as valid lucide-react icon names; they are resolved
 * dynamically in `src/components/ui/Icon.tsx`.
 */

export const brand = {
  name: 'Modira',
  nameFa: 'مدیرا',
  tagline: 'AI Social Media Admin OS',
  taglineFa: 'سیستم‌عامل هوشمند ادمین فروش اجتماعی',
  sloganEn: 'Your AI admin for social commerce.',
  sloganFa: 'ادمین هوشمند فروش اجتماعی شما',
} as const;

/** Primary calls to action. Swap `href` for your real demo form / contact link. */
const frontendBaseUrl = (import.meta.env.VITE_FRONTEND_URL || 'http://localhost:5173').replace(
  /\/$/,
  '',
);

export const cta = {
  primary: { label: 'درخواست دمو', href: '#demo' },
  secondary: { label: 'مشاهده قابلیت‌ها', href: '#features' },
  consult: { label: 'دریافت مشاوره پایلوت', href: '#demo' },
  panel: { label: 'ورود به پنل', href: `${frontendBaseUrl}/login` },
} as const;

export const nav = {
  links: [
    { label: 'معرفی', href: '#intro' },
    { label: 'قابلیت‌ها', href: '#features' },
    { label: 'سناریوها', href: '#scenarios' },
    { label: 'کانال‌ها', href: '#channels' },
    { label: 'امنیت', href: '#security' },
    { label: 'پایلوت', href: '#pilot' },
  ],
} as const;

export const hero = {
  eyebrow: 'AI Social Media Admin OS',
  headline: 'مدیرا؛ ادمین هوشمند فروش اجتماعی شما',
  subheadline:
    'مدیرا پیام‌های مشتریان را در اینستاگرام، واتساپ، تلگرام، بله، روبیکا و کانال‌های دیگر مدیریت می‌کند؛ سؤال‌ها را پاسخ می‌دهد، محصول را تشخیص می‌دهد، سفارش می‌سازد و هرجا لازم باشد مکالمه را به ادمین انسانی تحویل می‌دهد.',
  badges: [
    'Automation First',
    'LLM Fallback',
    'Human Handoff',
    'Multi-channel',
    'Pilot Ready',
  ],
} as const;

export const problem = {
  id: 'intro',
  title: 'ادمین سنتی برای فروش اجتماعی کافی نیست',
  subtitle:
    'حجم پیام بالا می‌رود، کانال‌ها زیاد می‌شوند و خطای انسانی فروش را از دست می‌دهد.',
  items: [
    {
      icon: 'Network',
      title: 'پراکندگی کانال‌ها',
      text: 'پیام‌ها در چند کانال پراکنده‌اند و هیچ نمای واحدی وجود ندارد.',
    },
    {
      icon: 'Timer',
      title: 'انتظار برای پاسخ سریع',
      text: 'مشتری‌ها سریع پاسخ می‌خواهند و تأخیر یعنی از دست رفتن فروش.',
    },
    {
      icon: 'Tags',
      title: 'دقت اطلاعات محصول',
      text: 'اطلاعات محصول، قیمت و موجودی همیشه باید دقیق و به‌روز باشد.',
    },
    {
      icon: 'ClipboardList',
      title: 'ثبت سفارش دستی',
      text: 'ثبت سفارش دستی زمان‌بر و پرخطاست و باعث دوباره‌کاری می‌شود.',
    },
    {
      icon: 'Gauge',
      title: 'کندی در ساعات شلوغ',
      text: 'ادمین انسانی در ساعات شلوغ کند می‌شود و صف پاسخ‌گویی طولانی می‌شود.',
    },
    {
      icon: 'LineChart',
      title: 'نبود دید تحلیلی',
      text: 'فروشگاه دید تحلیلی از مکالمات و فرصت‌های فروش ندارد.',
    },
  ],
} as const;

export const solution = {
  title: 'مدیرا چه کاری انجام می‌دهد؟',
  subtitle:
    'مدیرا پیام‌ها، کاتالوگ، اتوماسیون، LLM و ادمین‌های انسانی را در یک سیستم‌عامل واحد به هم متصل می‌کند.',
  flow: [
    { icon: 'MessageSquare', label: 'پیام مشتری' },
    { icon: 'ScanSearch', label: 'تشخیص سناریو' },
    { icon: 'PackageSearch', label: 'اتصال به محصول یا سفارش' },
    { icon: 'Workflow', label: 'اتوماسیون قطعی' },
    { icon: 'Sparkles', label: 'LLM در صورت نیاز' },
    { icon: 'CheckCheck', label: 'پاسخ، سفارش یا تحویل به انسان' },
  ],
} as const;

export const philosophy = {
  title: 'اتوماسیون اول؛ هوش مصنوعی فقط جایی که لازم است',
  subtitle:
    'مدیرا همه‌چیز را کورکورانه از LLM نمی‌پرسد. اول از قواعد قطعی، داده‌های کاتالوگ، هندلر سناریو و منطق کسب‌وکار استفاده می‌کند. LLM فقط برای ابهام، زبان طبیعی، خلاصه‌سازی، سؤال‌های پیچیده و پیش‌نویس محتوا به‌کار می‌رود. تصمیم‌های حساس مثل قیمت، موجودی، پرداخت و وضعیت سفارش همیشه توسط سرویس‌های بک‌اند کنترل می‌شوند.',
  pillars: [
    {
      order: '۰۱',
      tag: 'Automation First',
      icon: 'Workflow',
      title: 'اتوماسیون اول',
      text: 'قواعد قطعی، داده‌های کاتالوگ و منطق کسب‌وکار، خط مقدم پاسخ‌گویی هستند.',
    },
    {
      order: '۰۲',
      tag: 'LLM Fallback',
      icon: 'Sparkles',
      title: 'هوش مصنوعی دوم',
      text: 'LLM فقط در ابهام، زبان طبیعی، خلاصه و تولید محتوا وارد می‌شود؛ نه در تصمیم‌های حساس.',
    },
    {
      order: '۰۳',
      tag: 'Human Handoff',
      icon: 'UserCheck',
      title: 'تحویل به انسان سوم',
      text: 'موارد ریسکی و حساس با خلاصه و زمینهٔ کامل به ادمین انسانی واگذار می‌شوند.',
    },
  ],
} as const;

export const features = {
  id: 'features',
  title: 'همه ابزارهای ادمین اجتماعی در یک سیستم',
  subtitle:
    'یک سیستم‌عامل کامل برای مدیریت گفت‌وگو، فروش و پشتیبانی در شبکه‌های اجتماعی.',
  items: [
    { icon: 'Inbox', title: 'این‌باکس یکپارچه', text: 'همه پیام‌های کانال‌ها در یک نمای واحد و قابل‌مدیریت.' },
    { icon: 'MessageSquareReply', title: 'پاسخ هوشمند', text: 'پاسخ دقیق و متناسب با زمینه، مبتنی بر داده‌های واقعی فروشگاه.' },
    { icon: 'ScanSearch', title: 'تشخیص سناریو', text: 'فهم نیت مشتری و انتخاب مسیر درست برای هر مکالمه.' },
    { icon: 'BookOpen', title: 'فهم کاتالوگ', text: 'درک محصول، دسته، برند، ویژگی و گزینه‌های مختلف.' },
    { icon: 'Search', title: 'جست‌وجوی محصول', text: 'فیلتر بر اساس دسته، برند، بازهٔ قیمت و ویژگی‌ها.' },
    { icon: 'ShoppingCart', title: 'ساخت سفارش', text: 'تبدیل مکالمه به پیش‌نویس سفارش، بدون خطای دستی.' },
    { icon: 'CreditCard', title: 'پرداخت و ارسال', text: 'پشتیبانی از جریان پرداخت و پیگیری ارسال و رهگیری.' },
    { icon: 'LifeBuoy', title: 'پشتیبانی و شکایت', text: 'مدیریت شکایت، مرجوعی و تعویض با مسیرهای مشخص.' },
    { icon: 'UserCheck', title: 'تحویل به ادمین انسانی', text: 'واگذاری هوشمند موارد حساس با زمینهٔ کامل.' },
    { icon: 'BarChart3', title: 'تحلیل عملکرد', text: 'نرخ اتوماسیون، تبدیل، تحویل و عملکرد کانال‌ها.' },
    { icon: 'FlaskConical', title: 'شبیه‌ساز سناریو', text: 'اجرای کنترل‌شدهٔ سناریوها پیش از فعال‌سازی واقعی.' },
    { icon: 'PenLine', title: 'تولید محتوای کمکی', text: 'کپشن، متن استوری و پیام کمپین به‌عنوان پیش‌نویس برای ادمین.' },
  ],
} as const;

export type ChatBubble = {
  from: 'customer' | 'modira';
  text: string;
  attachment?: { type: 'post' | 'story' | 'product' | 'order'; label: string };
  label?: string;
};

export const scenarios = {
  id: 'scenarios',
  title: 'مدیرا سناریو را می‌فهمد، نه فقط متن پیام را',
  subtitle:
    'مدیرا زمینهٔ مکالمه، محتوای ارجاعی و وضعیت واقعی فروشگاه را با هم در نظر می‌گیرد.',
  items: [
    {
      icon: 'ImageUp',
      tag: 'Reference Resolution',
      title: 'ارجاع به پست و ادامهٔ مکالمه',
      bubbles: [
        { from: 'customer', text: 'قیمت این چنده؟', attachment: { type: 'post', label: 'پست ارسالی' } },
        { from: 'customer', text: 'همونو می‌خوام' },
        {
          from: 'modira',
          text: 'پست را شناسایی کردم؛ محصول را پیدا کردم و موجودی را بررسی کردم. فقط رنگ را انتخاب کنید تا پیش‌نویس سفارش را بسازم.',
          label: 'پست → محصول → موجودی → پیش‌نویس سفارش',
        },
      ] as ChatBubble[],
    },
    {
      icon: 'Clapperboard',
      tag: 'Story Context',
      title: 'پاسخ به ریپلای استوری',
      bubbles: [
        { from: 'customer', text: 'این موجوده؟', attachment: { type: 'story', label: 'ریپلای استوری' } },
        {
          from: 'modira',
          text: 'استوری مربوط را تشخیص دادم؛ بر اساس کاتالوگ و موجودی پاسخ می‌دهم: بله، در سایز ۳۸ تا ۴۲ موجود است.',
          label: 'استوری → محصول → موجودی',
        },
      ] as ChatBubble[],
    },
    {
      icon: 'ListFilter',
      tag: 'Product Discovery',
      title: 'جست‌وجوی فیلترشده در تلگرام',
      bubbles: [
        { from: 'customer', text: 'همه چکش‌های برند بوش زیر ۵ میلیون رو بفرست' },
        {
          from: 'modira',
          text: 'کاتالوگ را فیلتر کردم و ۴ محصول پیدا شد. فهرست را می‌فرستم؛ با شماره یا دکمه انتخاب کنید.',
          label: 'فیلتر برند + قیمت → فهرست محصول',
          attachment: { type: 'product', label: 'چکش بوش — ۴ نتیجه' },
        },
      ] as ChatBubble[],
    },
    {
      icon: 'Truck',
      tag: 'Order Tracking',
      title: 'پیگیری وضعیت سفارش',
      bubbles: [
        { from: 'customer', text: 'سفارشم کجاست؟' },
        {
          from: 'modira',
          text: 'سفارش شما در حال ارسال است. کد رهگیری و زمان تقریبی تحویل را برایتان فرستادم.',
          label: 'بررسی وضعیت سفارش → اطلاعات رهگیری',
          attachment: { type: 'order', label: 'سفارش #۱۰۹۲ — در حال ارسال' },
        },
      ] as ChatBubble[],
    },
    {
      icon: 'ShieldAlert',
      tag: 'Risk → Human Handoff',
      title: 'تشخیص ریسک و تحویل به انسان',
      bubbles: [
        { from: 'customer', text: 'کالای اشتباه فرستادید، خیلی ناراضی‌ام!' },
        {
          from: 'modira',
          text: 'ریسک را تشخیص دادم؛ خلاصهٔ موضوع و پیشنهاد پاسخ را آماده کردم و مکالمه را با زمینهٔ کامل به ادمین انسانی تحویل دادم.',
          label: 'تشخیص ریسک → خلاصه → پیشنهاد پاسخ → تحویل به انسان',
        },
      ] as ChatBubble[],
    },
  ],
} as const;

export const channels = {
  id: 'channels',
  title: 'همه کانال‌ها؛ یک مغز عملیاتی',
  subtitle:
    'هر کانال آداپتور مخصوص خودش را دارد، اما منطق کسب‌وکار یکپارچه است. یعنی همان منطق محصول، سفارش، اتوماسیون و پشتیبانی روی همهٔ کانال‌ها کار می‌کند.',
  items: [
    { icon: 'Instagram', name: 'Instagram', nameFa: 'اینستاگرام' },
    { icon: 'MessageCircle', name: 'WhatsApp', nameFa: 'واتساپ' },
    { icon: 'Send', name: 'Telegram', nameFa: 'تلگرام' },
    { icon: 'MessageSquareDot', name: 'Bale', nameFa: 'بله' },
    { icon: 'MessagesSquare', name: 'Rubika', nameFa: 'روبیکا' },
    { icon: 'Plus', name: 'Future channels', nameFa: 'کانال‌های آینده' },
  ],
} as const;

export const catalog = {
  title: 'از مکالمه تا سفارش، بدون خطای انسانی',
  subtitle: 'مدیرا گفت‌وگو را به داده‌های واقعی محصول متصل می‌کند.',
  items: [
    { icon: 'Package', label: 'محصولات' },
    { icon: 'FolderTree', label: 'دسته‌بندی‌ها' },
    { icon: 'SlidersHorizontal', label: 'ویژگی‌ها' },
    { icon: 'Layers', label: 'تنوع و گزینه‌ها' },
    { icon: 'Boxes', label: 'موجودی' },
    { icon: 'Tag', label: 'قیمت‌ها' },
    { icon: 'CreditCard', label: 'قواعد پرداخت' },
    { icon: 'Truck', label: 'قواعد ارسال' },
    { icon: 'ScrollText', label: 'سیاست‌های فروشگاه' },
  ],
  emphasis:
    'LLM هرگز قیمت یا موجودی را از خودش نمی‌سازد. فقط به فهم زبان کمک می‌کند؛ پاسخ نهایی از سیستم می‌آید.',
} as const;

export const dashboard = {
  title: 'پنلی برای کنترل، نه فقط مشاهده',
  subtitle:
    'همهٔ ماژول‌های عملیاتی در یک داشبورد منسجم، با ردگیری کامل تصمیم‌ها.',
  modules: [
    { icon: 'Inbox', label: 'این‌باکس یکپارچه' },
    { icon: 'MessagesSquare', label: 'جزئیات مکالمه' },
    { icon: 'PackageSearch', label: 'زمینهٔ محصول' },
    { icon: 'ShoppingCart', label: 'پیش‌نویس سفارش' },
    { icon: 'GitBranch', label: 'ردگیری تصمیم' },
    { icon: 'Sparkles', label: 'نشان اتوماسیون/LLM' },
    { icon: 'PackageCheck', label: 'بستهٔ تحویل به انسان' },
    { icon: 'BarChart3', label: 'تحلیل‌ها' },
    { icon: 'AlertTriangle', label: 'کارهای ناموفق' },
    { icon: 'FlaskConical', label: 'شبیه‌ساز سناریو' },
    { icon: 'Wand2', label: 'وظایف هوش مصنوعی ادمین' },
  ],
} as const;

export const aiTasks = {
  title: 'کمک به ادمین، فراتر از پاسخ‌گویی',
  subtitle: 'قابلیت‌هایی آماده برای آینده که بهره‌وری ادمین را چند برابر می‌کنند.',
  items: [
    { icon: 'MessageSquareReply', label: 'پیشنهاد پاسخ' },
    { icon: 'FileText', label: 'خلاصه مکالمه' },
    { icon: 'HelpCircle', label: 'استخراج سؤالات پرتکرار' },
    { icon: 'PenLine', label: 'پیش‌نویس کپشن پست' },
    { icon: 'Clapperboard', label: 'متن استوری' },
    { icon: 'Megaphone', label: 'پیام کمپین' },
    { icon: 'UserPlus', label: 'پیام بازگشت مشتری' },
    { icon: 'GitCompare', label: 'مقایسه محصول' },
  ],
  note: 'محتوای تولیدشده نیاز به تأیید ادمین دارد. در نسخهٔ نخست، انتشار خودکار وجود ندارد.',
} as const;

export const security = {
  id: 'security',
  title: 'طراحی‌شده برای فروش واقعی؛ نه فقط دمو',
  subtitle: 'کنترل‌ها و گاردریل‌هایی که مدیرا را برای فروش واقعی امن می‌کنند.',
  items: [
    { icon: 'Database', text: 'قیمت و موجودی از دیتابیس خوانده می‌شود.' },
    { icon: 'ShieldCheck', text: 'پرداخت فقط از مسیر امن انجام می‌شود.' },
    { icon: 'ClipboardCheck', text: 'سفارش بدون تأیید نهایی نمی‌شود.' },
    { icon: 'Lock', text: 'LLM تصمیم حساس نمی‌گیرد.' },
    { icon: 'UserCheck', text: 'پیام‌های حساس به ادمین انسانی تحویل می‌شود.' },
    { icon: 'FileSearch', text: 'همهٔ تصمیم‌ها trace و audit می‌شوند.' },
    { icon: 'CircleStop', text: 'Emergency stop برای توقف اتوماسیون وجود دارد.' },
  ],
} as const;

export const pilot = {
  id: 'pilot',
  title: 'از حالت Copilot شروع کنید، بعد خودکار شوید',
  subtitle:
    'یک مسیر مرحله‌به‌مرحله و کنترل‌شده تا فروشگاه شما با اطمینان خودکار شود.',
  stages: [
    { icon: 'PlugZap', title: 'اتصال کانال‌ها', text: 'کانال‌های فروش را به مدیرا متصل کنید.' },
    { icon: 'Upload', title: 'ورود کاتالوگ', text: 'محصولات، قیمت و موجودی وارد سیستم می‌شود.' },
    { icon: 'FlaskConical', title: 'اجرای شبیه‌ساز سناریو', text: 'سناریوها را پیش از تماس واقعی آزمایش کنید.' },
    { icon: 'Eye', title: 'حالت Shadow', text: 'مدیرا بدون پاسخ‌دادن، عملکرد را تمرین می‌کند.' },
    { icon: 'UserCog', title: 'حالت Copilot', text: 'مدیرا پیشنهاد می‌دهد، ادمین تأیید می‌کند.' },
    { icon: 'Workflow', title: 'اتوماسیون کنترل‌شده', text: 'پاسخ‌های مطمئن به‌صورت خودکار انجام می‌شوند.' },
    { icon: 'TrendingUp', title: 'تحلیل و بهبود', text: 'با داده‌ها، اتوماسیون را گسترده‌تر و دقیق‌تر کنید.' },
  ],
} as const;

export const finalCta = {
  id: 'demo',
  title: 'ادمین شبکه‌های اجتماعی خود را هوشمند کنید',
  text: 'مدیرا می‌تواند با داده‌ها، کاتالوگ و کانال‌های واقعی فروشگاه شما در یک پایلوت کنترل‌شده تست شود.',
} as const;

export const footer = {
  brand: 'Modira',
  tagline: 'AI Social Media Admin OS',
  note: 'نسخهٔ پایلوت برای فروشگاه‌های آنلاین',
  linkGroups: [
    {
      title: 'محصول',
      links: [
        { label: 'قابلیت‌ها', href: '#features' },
        { label: 'سناریوها', href: '#scenarios' },
        { label: 'امنیت', href: '#security' },
        { label: 'پایلوت', href: '#pilot' },
      ],
    },
    {
      title: 'ارتباط',
      links: [
        { label: 'تماس', href: '#demo' },
        { label: 'درخواست دمو', href: '#demo' },
      ],
    },
  ],
} as const;
