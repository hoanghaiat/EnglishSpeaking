# Test log — English Speaking Practice

Nhật ký những gì đã được kiểm thử sau mỗi commit. Mỗi mục ghi: commit, nội
dung chính, kết quả test tự động, kiểm thử thủ công (nếu có) và môi trường.

> Ghi chú: test venv của Muse nằm tại `~/workspace/.venv-esp5` (Django 5.2.17)
> và `~/workspace/.venv-esp` (Django 4.x). Hoàng chạy local bằng
> `D:\Automation\EnglishSpeaking\.venv\Scripts\python.exe`.

---

## <next> — Review round 4 (2026-10-14)

Nội dung: class gộp vào tab Links & Practice (bỏ tab Classes riêng), nút ×
xóa nhanh học sinh khỏi lớp; fix modal class (checkbox list, teacher preselect);
tạo xong ở yên tab hiện tại (sessionStorage); icon ⓘ How-it-works; bỏ alert
"No courses yet" và comment template bị lộ; People hiện số lượng theo role (bỏ
badge); "Is active" → "Active"; help text cho field Order; đổi password trong
My Profile; nới password validators (tối thiểu 6 ký tự, bỏ "too common");
dashboard thêm Total Classes (admin) / My Classes (teacher); changelog dạng
table + tab lọc theo category; preview lesson bằng modal (không chuyển trang);
hiệu ứng particle theo pointer ở nền site.

- `manage.py check`: no issues.
- Full suite: **174/174 passed** (Django 5.2.17).
- `test_manage`: **99/99 passed** (Django 4.x).
- Thủ công (headless Chromium): modal class layout đẹp; preview modal không
  chuyển trang; tab persistence sau reload; info popover toggle; particle canvas
  hiển thị; phát hiện & fix 2 bug template comment (`{ #` có dấu cách, comment
  nhiều dòng không được Django strip).
- Bug đáng chú ý đã fix: `StudyClassForm` validate unique bỏ qua `teacher`
  (không phải form field) → override `_get_validation_exclusions`.

## 6259753 — Classes, changelog, scoped teacher management, filters, collapse tree, login→home, UTC+7, toast center 3s (2026-10-14)

Nội dung: model `StudyClass` + `ChangeLog` (migration 0003); teacher tạo lớp,
liên kết student–parent tối đa 2; changelog hiển thị ở dashboard thay My Account
(admin xem tất cả, teacher xem của mình + admin liên quan); `/manage/` mở cho
teacher (scoped); Speaking Lessons thành tab trong Management; giao bài theo
lớp/cá nhân; filter 4 vùng; cây Learning Content collapse mặc định; toast căn
giữa màn hình, tự tắt 3s; session config rõ ràng; profile tách Staff/Superuser;
`TIME_ZONE = Asia/Ho_Chi_Minh`.

- `manage.py check`: no issues.
- Full suite: **154/154 passed** (Django 5.2.17).
- `test_manage`: **79/79 passed** (Django 4.x).
- Thủ công (headless Chromium): tab deep-link `?tab=...` đúng cho cả 5 tab;
  twisty collapse/expand từng cấp; login redirect về `/`; teacher chỉ thấy
  học sinh/phụ huynh của mình; changelog visibility đúng role; cookie
  remember-me có expiry / không remember-me là session-only; logout hủy session.

## d24d0ba — Review round 2 (2026-10-14)

Nội dung: toast căn giữa trên; Management thành link thẳng (bỏ dropdown);
dashboard admin gọn (bỏ Student Practice Status); `/admin/speaking_practice/`
redirect về `/manage/`; profile mở rộng (đầy đủ thông tin + granted
permissions); site login có Remember me + `autocomplete="new-password"`.

- `manage.py check`: no issues.
- Full suite: **124/124 passed** (Django 5.2.17); `test_manage` xanh trên Django 4.x.
- Thủ công: site login có 1 checkbox `#remember_me`; password input báo
  `autocomplete="new-password"`; profile render đầy đủ trường.

## b1ce431 — One-page Management Center (2026-10-14)

Nội dung: `/manage/` gom 3 tab (Learning Content, People, Links & Practice);
cây Course > Chapter > Lesson > Exercise; quản lý user qua modal (tạo đúng role
profile, chặn xóa chính mình / hạ quyền admin của mình); liên kết
teacher–student, student–parent; assigned lessons; recent attempts (delete-only).

- Full suite: **117/117 passed** (Django 5.2.17); `test_manage` **50/50** (Django 4.x).

## ac00bd6 — Logout/login UX, opt-in Remember me, floating toast, unified header (2026-10-14)

Nội dung: admin logout đi thẳng login (bỏ trang trung gian); login có Remember
me opt-in (không check = session theo browser); toast nổi không đẩy layout;
header đồng nhất giữa site và admin; dashboard gọn.

- Full suite xanh trên Django 5.2.17 và Django 4.x (xem chi tiết trong GOAL.md).

---

## Quy ước test cho các commit tiếp theo

1. `manage.py check` — không có issue mới.
2. Full suite `manage.py test speaking_practice` trên Django 5.2.17 — phải xanh.
3. `test_manage` trên Django 4.x — phải xanh (tương thích ngược).
4. Tính năng UI mới: kiểm thử thủ công bằng headless Chromium (screenshot +
   thao tác) trước khi commit.
5. Ghi kết quả vào file này ngay trong commit.
