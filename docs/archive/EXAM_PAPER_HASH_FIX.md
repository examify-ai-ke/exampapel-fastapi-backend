# ExamPaper Model Hash Code Fix

## Issue
The `ExamPaper` model had a conflict where `hash_code` was defined both as:
1. A database field: `hash_code: Optional[str] = Field(nullable=False, unique=True, default=None)`
2. A computed property: `@property def hash_code(self): return self.calculate_hash`

This caused issues because:
- The database expects a stored value for indexing (unique=True)
- The property decorator tried to compute it dynamically
- The slug validator couldn't access hash_code during model creation

## Solution

### ✅ What Was Fixed

1. **Removed the conflicting `@property` decorator** for `hash_code`
   - `hash_code` is now purely a database field that gets auto-generated via validator

2. **Added `@validator` for `hash_code`**
   - Automatically generates hash during model creation if not provided
   - Uses exam paper attributes (title_id, year, institution_id, description_id, exam_date, duration)
   - Generates SHA-256 hash for uniqueness

3. **Simplified `slug` validator**
   - Now uses the first 12 characters of hash_code
   - More reliable since hash_code is available during validation

4. **Kept `identifying_name` as `@computed_field`**
   - This is correct - it's computed on-the-fly when accessed
   - Not stored in database
   - Used for display purposes

5. **Added helper method `_generate_hash()`**
   - Can be used to regenerate hash if needed
   - Includes all relationships (modules, instructions)

## How It Works Now

### During ExamPaper Creation:
```python
exam_paper = ExamPaper(
    title_id=uuid,
    year_of_exam="2024/2025",
    institution_id=uuid,
    description_id=uuid,
    exam_date=date(2024, 12, 15),
    exam_duration=120
)
# hash_code is auto-generated via validator
# slug is auto-generated from hash_code
```

### During ExamPaper Read:
```python
# hash_code: stored value from database
# identifying_name: computed on-the-fly
# slug: stored value from database
# questions_count: computed on-the-fly
```

## Key Differences

| Field | Storage | Generation | Purpose |
|-------|---------|------------|---------|
| `hash_code` | Database | Validator (on create) | Unique identifier, indexed |
| `slug` | Database | Validator (from hash_code) | URL-friendly identifier |
| `identifying_name` | Computed | On-access | Human-readable display name |
| `questions_count` | Computed | On-access | Dynamic count |

## Benefits

1. ✅ **No more conflicts** between database field and property
2. ✅ **Automatic hash generation** during model creation
3. ✅ **Database indexing works** properly (unique constraint)
4. ✅ **Slug generation is reliable** (uses stored hash_code)
5. ✅ **identifying_name remains dynamic** (always up-to-date)

## Migration Note

If you have existing exam papers in the database:
- Existing `hash_code` values will be preserved
- New exam papers will auto-generate hash_code
- No database migration needed (field definition unchanged)
