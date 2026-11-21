# Resource Hero reference for the Kicksaw org

Where a person's **allocation** lives. TaskRay says what they logged; Resource Hero says what they were staffed for. The report compares the two.

Verified against Kicksaw-Prod on 2026-09-18.

## The shape of it

| Object | Role |
| --- | --- |
| `ResourceHeroApp__Resource__c` | The person. One row, found by name |
| `ResourceHeroApp__Resource_Assignment__c` | One row per person per project. Carries the date range and the role |
| `ResourceHeroApp__Resource_Forecast__c` | The detail. **One row per day**, child of the assignment |

An assignment is not the same record as the Flux resource on the time record. A person has one Flux resource and one Resource Hero resource, plus one assignment per project they are staffed to.

## Reading the forecast

`ResourceHeroApp__Resource_Forecast__c` rows are **per day, not per week**. Forecast and actual live on separate rows: a forecast row carries `Forecast__c` with `Actual__c` at 0, and an actual row carries `Actual__c` with `Forecast__c` at 0. Summing one field over a date range is therefore safe and needs no filter on the other.

A full-time assignment at half a person's week shows as `Forecast__c = 4` on each of five rows, which is 20 hours for that week.

**Do not read allocation off the assignment record.** `ResourceHeroApp__Auto_Forecast_Hours__c` and `ResourceHeroApp__Remaining_Forecast_Hours__c` on the parent do not reconcile against the summed detail rows, and their meaning is not documented. The forecast rows are the source of truth.

**Count only assignments on a Resource Hero project.** An assignment points at one related record, and `ResourceHeroApp__Related_Record_Type__c` says which kind: `RH Project` or `Opportunity`. An Opportunity assignment is pipeline staffing, for a deal with no project yet, and has no TaskRay project to log against. When the deal turns into work, the project gets its own assignment, and the Opportunity one may be archived with its forecast still in place, so counting both adds the same hours twice. `ResourceHeroApp__Related_Record__c` holds the record's name as an HTML link. Neither `Archive` nor `Staffing_Status__c` tells the two apart: archived project assignments are real past staffing, and the status is blank or Open on both kinds.

**Never use Resource Hero's actuals.** `Actual__c` is synced from time records on a lag and was observed a full week behind on a live org. Actuals always come from `TASKRAY__trTaskTime__c`. Resource Hero is read for the forecast side only.

## Queries

**The person's resource record:**

```
SELECT Id, Name FROM ResourceHeroApp__Resource__c WHERE Name LIKE '%<last name>%'
```

**The user's resource record, by user** (setup uses this; it needs no name match):

```
SELECT Id FROM ResourceHeroApp__Resource__c WHERE ResourceHeroApp__User__c = '<user_id>' AND ResourceHeroApp__Archive__c = false
```

**Setup assignments** (the projects someone is staffed on now, with the TaskRay project each links to; setup offers these as candidates):

```
SELECT Id, ResourceHeroApp__RH_Project__r.Name, ResourceHeroApp__RH_Project__r.TaskRay_Project__c, ResourceHeroApp__End_Date__c, ResourceHeroApp__Role__c FROM ResourceHeroApp__Resource_Assignment__c WHERE ResourceHeroApp__Resource__c = '<resource_id>' AND ResourceHeroApp__Archive__c = false AND ResourceHeroApp__Is_Holiday_Time__c = false AND ResourceHeroApp__Is_Time_Off_PTO__c = false AND (ResourceHeroApp__End_Date__c >= TODAY OR ResourceHeroApp__End_Date__c = null) ORDER BY ResourceHeroApp__Start_Date__c
```

An assignment with no `TaskRay_Project__c` can't take time records; leave it out of the options.

**Current assignments** (one per project; gives the `rh_assignment_id` saved per project in the profile):

```
SELECT Id, Name, ResourceHeroApp__RH_Project__r.Name, ResourceHeroApp__Start_Date__c, ResourceHeroApp__End_Date__c, ResourceHeroApp__Role__c FROM ResourceHeroApp__Resource_Assignment__c WHERE ResourceHeroApp__Resource__c = '<resource_id>' AND ResourceHeroApp__Archive__c = false AND ResourceHeroApp__End_Date__c >= TODAY ORDER BY ResourceHeroApp__Start_Date__c
```

A project with no assignment row is not staffed. That is a real signal, not an error: report the logged hours against no allocation and say so.

**Allocated hours for a period**, per assignment:

```
SELECT ResourceHeroApp__Resource_Assignment__c, SUM(ResourceHeroApp__Forecast__c) fc FROM ResourceHeroApp__Resource_Forecast__c WHERE ResourceHeroApp__Resource_Assignment__c IN (<assignment ids>) AND ResourceHeroApp__ForecastDate__c >= <start> AND ResourceHeroApp__ForecastDate__c <= <end> GROUP BY ResourceHeroApp__Resource_Assignment__c
```

**Aggregates do not render under `--result-format csv`.** The `SUM` column comes back empty. Use `--json` and read the alias off the record. This is a property of the CLI, not the query.
