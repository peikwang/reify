const LEADING_REQUEST =
  /^(请|请帮我|帮我|帮忙|麻烦|我想|我要|想要|需要|能不能|可以)\s*/;
const LEADING_FOR = /^(为|给)(一家|一个|一款|某家|某|我的|我们)?\s*/;
const LEADING_QUANTIFIER = /^(一家|一个|一款|一段|一张|一组|一套|一份|我的|我们的)\s*/;
const VERB_WORDS = [
  "制作一个",
  "生成一个",
  "创建一个",
  "设计一个",
  "开发一个",
  "写一个",
  "搭一个",
  "实现一个",
  "做一个",
  "做个",
  "制作",
  "生成",
  "创建",
  "设计",
  "开发",
  "写个",
  "实现",
];
const LEADING_DESCRIPTOR = /^(有[^，。]{0,8}感的|有|的)\s*/;
const FIRST_CLAUSE = /[，。！？；,.!?;:：\n].*$/;

export function suggestProjectTitle(
  prompt: string,
  capabilityLabel = "",
): string {
  let text = prompt.replace(/\s+/g, " ").trim();
  if (!text) return capabilityLabel || "未命名项目";
  text = text.replace(FIRST_CLAUSE, "").trim();

  let subject = "";
  let object = text;
  let verbIndex = -1;
  let verbWord = "";
  for (const word of VERB_WORDS) {
    const index = text.lastIndexOf(word);
    if (
      index > verbIndex ||
      (index === verbIndex && index >= 0 && word.length > verbWord.length)
    ) {
      verbIndex = index;
      verbWord = word;
    }
  }
  if (verbIndex >= 0) {
    subject = text.slice(0, verbIndex).trim();
    object = text.slice(verbIndex + verbWord.length).trim();
  }

  subject = subject
    .replace(LEADING_REQUEST, "")
    .replace(LEADING_FOR, "")
    .replace(LEADING_QUANTIFIER, "")
    .trim();
  object = object
    .replace(LEADING_QUANTIFIER, "")
    .replace(LEADING_DESCRIPTOR, "")
    .trim();

  let title = subject && object ? subject + object : object || text;
  title = title.replace(/\s+/g, " ").trim();

  const english = /^[A-Za-z0-9\s'’-]+$/.test(title);
  if (english) {
    title = title.split(/\s+/).slice(0, 6).join(" ");
  }
  const limit = english ? 32 : 18;
  if (title.length > limit) title = title.slice(0, limit).trim();
  return title || capabilityLabel || "未命名项目";
}
