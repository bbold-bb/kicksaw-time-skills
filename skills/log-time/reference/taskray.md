# TaskRay reference for the Kicksaw org

Org-wide facts. Nothing here is specific to one user. Verified against Kicksaw-Prod on 2026-09-15; if an insert is rejected on a picklist or record type, re-describe the object before assuming this file is right.

Every query below takes `-o <org alias>` from the profile. `<username>`, `<user_id>`, and the project and task Ids come from the profile too.

## Objects

| Object | Role |
| --- | --- |
| `TASKRAY__trTaskTime__c` | The time record. The only object this skill writes |
| `TASKRAY__Project__c` | The project |
| `TASKRAY__Project_Task__c` | The task a time record must point at. `TASKRAY__Task__c` is required on the time record |
| `TASKRAY__trContributor__c` | TaskRay Team rows. **Not reliable for "which projects am I on"**: they lag reality by years. Do not use them as the membership check |

## Setup and drift queries

**Identity.** `sf org display user -o <alias> --json` returns `id` and `username`.

**Timezone** (offered as the second timezone option in setup):

```
SELECT TimeZoneSidKey FROM User WHERE Id = '<user_id>'
```

**Active projects matching a client name:**

```
SELECT Id, Name, TASKRAY__trAccount__r.Name, TASKRAY__Project_End__c, Delivery_Team__c, Type__c FROM TASKRAY__Project__c WHERE Name LIKE '%<client>%' AND TASKRAY__Status__c = false AND TASKRAY__trCompleted__c = false AND Archived_Date__c = null AND TASKRAY__trTemplate__c = false AND Parent_Project__c = false ORDER BY Name
```

`TASKRAY__Status__c` is a checkbox that is true when the project is closed.

**The internal project** is an open project the org marks as Internal, not one found by name:

```
SELECT Id, Name, TASKRAY__Project_End__c FROM TASKRAY__Project__c WHERE Type__c = 'Internal' AND TASKRAY__Status__c = false AND TASKRAY__trCompleted__c = false AND Archived_Date__c = null AND TASKRAY__trTemplate__c = false ORDER BY Name
```

More than one can be open at once (an old period's copy is often left open). Offer them as options; the one picked is saved in the profile.

**Recent history** (projects the user logged to in the last 90 days):

```
SELECT TASKRAY__Project__c, TASKRAY__Project__r.Name, MAX(TASKRAY__Date__c), COUNT(Id) FROM TASKRAY__trTaskTime__c WHERE TASKRAY__Owner__r.Username = '<username>' AND TASKRAY__Date__c = LAST_N_DAYS:90 GROUP BY TASKRAY__Project__c, TASKRAY__Project__r.Name ORDER BY MAX(TASKRAY__Date__c) DESC
```

**Live task for a project.** A project's time-entry task is its unarchived task. When a task rolls over, the old one is archived and a new one is added, so only the newest is live. The org accepts inserts against an archived task silently, so always resolve by the archived flag, never by remembering an Id. Use the project's only unarchived task, whatever its name, and show its name. Zero or several is the same as no live task: show them and ask, and save the one picked.

```
SELECT Id, Name, TASKRAY__Project__c FROM TASKRAY__Project_Task__c WHERE TASKRAY__Project__c = '<project_id>' AND TASKRAY__Archived__c = false
```

**Drift check, tasks** (all the profile's task Ids in one call):

```
SELECT Id, Name, TASKRAY__Project__r.Name, TASKRAY__Archived__c FROM TASKRAY__Project_Task__c WHERE Id IN (<task ids>)
```

**Drift check, projects:**

```
SELECT Id, Name, TASKRAY__Status__c, TASKRAY__trCompleted__c, Archived_Date__c, TASKRAY__Project_End__c FROM TASKRAY__Project__c WHERE Id IN (<project ids>)
```

## Run queries

**Last records** (Step 1 boundary):

```
SELECT Name, TASKRAY__Date__c, TASKRAY__Project__r.Name, Activity_Type__c, TASKRAY__Hours__c, CreatedDate FROM TASKRAY__trTaskTime__c WHERE TASKRAY__Owner__r.Username = '<username>' ORDER BY TASKRAY__Date__c DESC LIMIT 20
```

**Records in scope** (Step 1 reconciliation; substitute the scope dates):

```
SELECT Id, Name, TASKRAY__Date__c, TASKRAY__Project__c, TASKRAY__Project__r.Name, Activity_Type__c, TASKRAY__Hours__c, Notes__c, Notes_Long_Text__c, CreatedDate FROM TASKRAY__trTaskTime__c WHERE TASKRAY__Owner__r.Username = '<username>' AND TASKRAY__Date__c >= <start> AND TASKRAY__Date__c <= <end> ORDER BY TASKRAY__Date__c, TASKRAY__Project__r.Name, Activity_Type__c
```

**Created today** (Step 7 verify):

```
SELECT Name, TASKRAY__Date__c, TASKRAY__Project__r.Name, Activity_Type__c, TASKRAY__Hours__c, Monthly_Billing_Summary__c, Pay_Period__c, Owner_Role__c FROM TASKRAY__trTaskTime__c WHERE TASKRAY__Owner__r.Username = '<username>' AND CreatedDate = TODAY ORDER BY TASKRAY__Date__c
```

**Work pattern** (Setup step 8 and the 30-day check: client hours by Activity Type, then the user's latest role, which can't be grouped on):

```
SELECT Activity_Type__c, SUM(TASKRAY__Hours__c) hours FROM TASKRAY__trTaskTime__c WHERE TASKRAY__Owner__r.Username = '<username>' AND TASKRAY__Date__c = LAST_N_DAYS:90 AND RecordType.DeveloperName = 'Client_Work' GROUP BY Activity_Type__c ORDER BY SUM(TASKRAY__Hours__c) DESC
```

```
SELECT Owner_Role__c FROM TASKRAY__trTaskTime__c WHERE TASKRAY__Owner__r.Username = '<username>' AND Owner_Role__c != null ORDER BY TASKRAY__Date__c DESC LIMIT 1
```

**Time dashboard** (Step 8 link; the company's Salesforce dashboard of the same records). Personal copies can share the title: prefer the one in the shared *Pilot - Time Logging Dashboards* folder, else the newest.

```
SELECT Id, FolderName FROM Dashboard WHERE Title = 'My Hours - Dashboard 2.0' ORDER BY LastModifiedDate DESC
```

## Record types on the time record

| Record type | Developer name | Use |
| --- | --- | --- |
| Client Work | `Client_Work` | Every client project |
| Internal Work | `Internal_Work` | The internal project. **Required**, or the restricted picklists reject the insert |

Look the Ids up once per run; never store them in this repo:

```
SELECT Id, DeveloperName FROM RecordType WHERE SobjectType = 'TASKRAY__trTaskTime__c' AND DeveloperName IN ('Client_Work', 'Internal_Work') AND IsActive = true
```

## Activity Type by record type

`Activity_Type__c` is restricted and scoped by record type. `Design`, `Build`, and `Release` exist in the global picklist but are on neither record type; never use them.

**Read the allowed values from the org** at setup, for each record type Id from the lookup above and each restricted field the payload sets (`Activity_Type__c`, `TASKRAY__trTimeType__c`, `Category__c`, `Non_Billable_Reason__c`):

```
sf api request rest "services/data/v67.0/ui-api/object-info/TASKRAY__trTaskTime__c/picklist-values/<record type id>/<field>" -o <alias>
```

The response's `values[].value` are the allowed values. Save them in the profile as `picklists`, keyed by record type then field. The table below is what the org allowed when this was written; when the org's list differs, the org wins.

| Client Work | Internal Work |
| --- | --- |
| Coding and Configuration | Admin and Overhead |
| Communications | Bench |
| Documentation | Learning and Development |
| Meeting | People and Team Activities |
| Travel | Presales |
| | PTO |
| | Recruiting |
| | Travel |

## Insert payload

Fields to set, and nothing more. The org's own entry flow only asks for owner, project, date, hours, billable, activity type, and notes; every other field here exists to make an API insert behave like a UI entry. Nothing gets added to this list without a reason stated in the run.

```json
{
  "RecordTypeId": "<Client Work record type Id, from the lookup above>",
  "TASKRAY__Project__c": "<project id from profile>",
  "TASKRAY__Task__c": "<task id from profile>",
  "TASKRAY__Date__c": "YYYY-MM-DD",
  "TASKRAY__Hours__c": 1.5,
  "TASKRAY__Owner__c": "<user_id from profile>",
  "TASKRAY__Billable__c": true,
  "TASKRAY__trTimeType__c": "Standard",
  "TASKRAY__trUnsavedTimeEntry__c": false,
  "Bypass_Time_Flow__c": false,
  "Activity_Type__c": "<from the Client Work list>",
  "Notes__c": "<comma-joined titles, truncated to 255>",
  "Notes_Long_Text__c": "<comma-joined titles, full>"
}
```

**Internal work** instead uses the Internal Work `RecordTypeId`, `TASKRAY__Billable__c: false`, `TASKRAY__trTimeType__c: "Internal"`, `Category__c: "Internal"`, `Non_Billable_Reason__c: "Not Applicable"`, and an `Activity_Type__c` from the Internal Work list. All internal time is non-billable.

**`Category__c` ("Work Type") stays blank on client work.** It was taken off the entry flow, it is not required, and the org leaves it null on nearly every record. Do not populate it or propose phase values for it. Internal records keep `Category__c: "Internal"` because that record type allows nothing else.

Notes live in `Notes__c` and `Notes_Long_Text__c`. `TASKRAY__Notes__c` stays null. Everything else (Monthly Billing Summary, Pay Period, Owner Role, Week, hour rollups, Hourly Rate, Resource Service Line, Team) is set by org automation on insert; never set it by hand.

### Required values

Every record must have all of these, with no blank, zero or placeholder value. `check_record.py` enforces that; whether a picklist value is allowed comes from the profile's `picklists`, and the org.

| Field | Must be |
| --- | --- |
| `RecordTypeId`, `TASKRAY__Project__c`, `TASKRAY__Task__c`, `TASKRAY__Owner__c` | A record Id |
| `TASKRAY__Date__c` | A real date, YYYY-MM-DD |
| `TASKRAY__Hours__c` | More than zero, in quarter hours |
| `TASKRAY__Billable__c` | Set to true or false, and false on internal time |
| `TASKRAY__trTimeType__c`, `Activity_Type__c` | An allowed value |
| `Notes__c`, `Notes_Long_Text__c` | Text |
| `Category__c`, `Non_Billable_Reason__c` | Internal time only: an allowed value |

Check the payload file first, and write only when it prints OK (`check_record.py payload.json --update` for a same-day merge).

**Insert one at a time** so the flows fire the way they do from the UI:

```
sf api request rest "services/data/v67.0/sobjects/TASKRAY__trTaskTime__c" --method POST --body "@payload.json" -o <alias>
```

## Same-day merge (update)

Only for a record created today in the same date, project, and Activity Type grouping. The body carries just the three fields that change:

```json
{ "TASKRAY__Hours__c": 1.5, "Notes__c": "<merged titles, truncated to 255>", "Notes_Long_Text__c": "<merged titles, full>" }
```

```
sf api request rest "services/data/v67.0/sobjects/TASKRAY__trTaskTime__c/<record id>" --method PATCH --body "@update.json" -o <alias>
```

## Known org behaviors

- Records dated in a previous month are rejected. Check before proposing a cross-month backfill.
- Inserts against an archived task succeed silently. That is why the drift check exists.
- Internal records have no Monthly Billing Summary after insert; client records should.
