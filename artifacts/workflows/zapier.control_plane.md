# Zapier Account Control Plane

## 1. Tables (Zapier Tables)

### 1.1. `accounts`
جدول لتخزين وإدارة حسابات Zapier المخصصة للفرق والمشاريع.

| Field Name         | Type           | Description                                       |
|--------------------|----------------|---------------------------------------------------|
| `account_id`       | `text` (UUID)  | المعرّف الفريد للحساب (Primary Key)               |
| `account_name`     | `text`         | اسم وصفي للحساب (e.g., "Marketing Team Account")  |
| `owner_name`       | `text`         | اسم مالك الحساب أو الفريق المسؤول                  |
| `owner_email`      | `email`        | البريد الإلكتروني للمالك للتواصل                  |
| `plan_type`        | `single_select`| نوع الخطة (e.g., "Team", "Company", "Free")       |
| `task_limit`       | `number`       | الحد الأقصى للمهام (Tasks) في دورة الفوترة         |
| `current_usage`    | `number`       | الاستخدام الحالي للمهام (يتم تحديثه دورياً)         |
| `billing_cycle_end`| `date`         | تاريخ انتهاء دورة الفوترة الحالية                 |
| `status`           | `single_select`| حالة الحساب (e.g., "Active", "Suspended", "Archived") |
| `created_at`       | `datetime`     | تاريخ إنشاء السجل                                  |
| `last_updated`     | `datetime`     | تاريخ آخر تحديث للسجل                             |

### 1.2. `alerts`
سجل لتتبع التنبيهات والإشعارات المرسلة بخصوص حالة الحسابات.

| Field Name      | Type           | Description                                     |
|-----------------|----------------|-------------------------------------------------|
| `alert_id`      | `text` (UUID)  | المعرّف الفريد للتنبيه (Primary Key)             |
| `account_id`    | `lookup`       | ربط بجدول `accounts`                           |
| `alert_type`    | `single_select`| نوع التنبيه (e.g., "DrainWarning", "Exhausted")  |
| `message`       | `text`         | نص رسالة التنبيه                                |
| `recipient`     | `email`        | البريد الإلكتروني للمستلم (مالك الحساب)          |
| `sent_at`       | `datetime`     | تاريخ ووقت إرسال التنبيه                        |
| `acknowledged`  | `checkbox`     | هل تم الإقرار بالتنبيه من قبل المالك؟            |

### 1.3. `intake`
جدول مؤقت لتسجيل طلبات الحسابات الجديدة قبل الموافقة عليها.

| Field Name      | Type           | Description                                    |
|-----------------|----------------|------------------------------------------------|
| `request_id`    | `text` (UUID)  | المعرّف الفريد للطلب (Primary Key)            |
| `requester_name`| `text`         | اسم مقدم الطلب                                |
| `requester_email`| `email`        | البريد الإلكتروني لمقدم الطلب                  |
| `project_name`  | `text`         | اسم المشروع أو الفريق الذي يحتاج الحساب       |
| `justification` | `long_text`    | مبررات الحاجة للحساب الجديد                    |
| `requested_plan`| `single_select`| الخطة المطلوبة (e.g., "Team", "Company")     |
| `status`        | `single_select`| حالة الطلب (e.g., "Pending", "Approved", "Rejected") |
| `submitted_at`  | `datetime`     | تاريخ تقديم الطلب                             |
| `reviewed_by`   | `text`         | اسم الشخص الذي راجع الطلب                    |
| `review_notes`  | `long_text`    | ملاحظات المراجعة                              |

---

## 2. Forms (Zapier Interfaces)

### 2.1. `new_account_intake`
نموذج لتقديم طلب حساب Zapier جديد. يكتب البيانات في جدول `intake`.

-   **Fields:**
    -   `requester_name` (Text, Required)
    -   `requester_email` (Email, Required)
    -   `project_name` (Text, Required)
    -   `justification` (Text Area, Required)
    -   `requested_plan` (Dropdown: "Team", "Company", Required)
-   **Action:**
    -   On submit, create a new record in the `intake` table.
    -   Trigger the `approval_flow` automation.

### 2.2. `status_update`
واجهة بسيطة (يمكن أن تكون داخلية) لتحديث حالة الحساب يدوياً.

-   **Fields:**
    -   `account_id` (Dropdown, linked to `accounts` table)
    -   `new_status` (Dropdown: "Active", "Suspended", "Archived", Required)
    -   `reason` (Text, Optional)
-   **Action:**
    -   On submit, find the record in the `accounts` table by `account_id` and update its `status`.

---

## 3. Automations (Zaps)

### 3.1. `drain_warning`
أتمتة لإرسال تحذير عند اقتراب استهلاك المهام من الحد الأقصى.

-   **Trigger:** Schedule (e.g., "Run daily at 9 AM").
-   **Action 1:** Find Records in `accounts` table where `status` is "Active".
-   **Action 2 (Loop):** For each account found:
    -   **Filter:** Only continue if `(current_usage / task_limit) > 0.85`.
    -   **Action 3:** Send Email (to `owner_email`) with a warning message.
    -   **Action 4:** Create Record in `alerts` table with `alert_type` = "DrainWarning".

### 3.2. `exhausted_notify`
أتمتة لإرسال إشعار فوري عند استنفاد رصيد المهام.

-   **Trigger:** Schedule (e.g., "Run every hour").
-   **Action 1:** Find Records in `accounts` table where `status` is "Active".
-   **Action 2 (Loop):** For each account found:
    -   **Filter:** Only continue if `current_usage >= task_limit`.
    -   **Action 3:** Send Email (to `owner_email` and ops admin) with an exhaustion notification.
    -   **Action 4:** Create Record in `alerts` table with `alert_type` = "Exhausted".
    -   **Action 5 (Optional):** Update Record in `accounts` table to set `status` to "Suspended".

### 3.3. `approval_flow`
أتمتة لإدارة دورة حياة الموافقة على الطلبات الجديدة.

-   **Trigger:** New Record in `intake` table.
-   **Action 1:** Send Email (to ops admin) with request details and approval/rejection links.
-   **Filter (for Approval):** Only continue if the "Approve" link is clicked.
    -   **Action 2:** Update Record in `intake` table to set `status` to "Approved".
    -   **Action 3:** Create Record in `accounts` table using data from the `intake` record.
    -   **Action 4:** Send Email (to `requester_email`) confirming the approval and providing account details.
-   **Filter (for Rejection):** Only continue if the "Reject" link is clicked.
    -   **Action 2:** Update Record in `intake` table to set `status` to "Rejected".
    -   **Action 3:** Send Email (to `requester_email`) informing them of the rejection.

---

## 4. Webhooks Endpoints

### 4.1. `POST /hooks/zapier/intake`
نقطة نهاية (Webhook) لاستقبال بيانات طلبات الحسابات الجديدة من أنظمة خارجية (إذا لزم الأمر).

-   **Trigger Type:** Webhooks by Zapier (Catch Hook).
-   **Action:** Create a new record in the `intake` table using the data from the webhook payload.
-   **Payload (Example):**
    ```json
    {
      "requester_name": "Fatima Al-Marzouqi",
      "requester_email": "fatima.m@example.com",
      "project_name": "Project Phoenix",
      "justification": "Automating CRM data sync.",
      "requested_plan": "Team"
    }
    ```

### 4.2. `POST /hooks/zapier/status`
نقطة نهاية لاستقبال تحديثات دورية حول استهلاك المهام من Zapier Manager API أو نظام مراقبة آخر.

-   **Trigger Type:** Webhooks by Zapier (Catch Hook).
-   **Action 1:** Find Record in `accounts` table where `account_id` matches the payload.
-   **Action 2:** Update Record found in Action 1 with the new `current_usage`.
-   **Payload (Example):**
    ```json
    {
      "account_id": "acc_123abc456def",
      "usage": {
        "tasks_used": 18500,
        "tasks_limit": 20000
      },
      "timestamp": "2023-10-27T10:00:00Z"
    }
    ```
