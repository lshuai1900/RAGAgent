-- 一次性修复脚本：释放历史 archived 知识库占用的名称
--
-- 背景：
--   早期版本删除知识库时仅把 status 改为 archived，未释放 name 占用。
--   由于 t_knowledge_base.name 上存在唯一约束，导致重新创建同名知识库
--   会被拦截（提示“知识库名称已存在”）。
--
--   新版本（见 service.KnowledgeService.delete_knowledge_base）删除时
--   会把 name 改为 ``{原名称}__deleted__{id}``，从源头避免该问题。
--   本脚本用于修复升级前已存在的历史 archived 记录。
--
-- 执行方式（任选其一）：
--   psql -d <db_url> -f scripts/fix_archived_kb_names.sql
--   或在 SQL 客户端中直接执行以下语句。
--
-- 幂等：WHERE name NOT LIKE '%__deleted__%' 保证可重复执行，
--       已修复过的记录不会被再次改动。
--
-- 长度安全：LEFT(name, 128 - LENGTH('__deleted__' || id)) 确保最终
--           长度不超过 name 列上限（128）。

BEGIN;

UPDATE t_knowledge_base
SET name = LEFT(name, 128 - LENGTH('__deleted__' || id)) || '__deleted__' || id,
    updated_at = NOW()
WHERE status = 'archived'
  AND name NOT LIKE '%__deleted__%';

COMMIT;

-- 校验（可选）：确认已无 archived 记录仍占用原始名称
-- SELECT id, name, status
-- FROM t_knowledge_base
-- WHERE status = 'archived'
-- ORDER BY updated_at DESC;
