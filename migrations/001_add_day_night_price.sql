-- 将 price_text / price_per_kwh 重命名为日间价格列，并新增夜间价格列
-- 历史数据均为白天采集，迁移后自动落入 day_price_* 列，night_price_* 为 NULL

ALTER TABLE connector_status_snapshots
    CHANGE COLUMN price_text    day_price_text    VARCHAR(200)  NULL DEFAULT NULL,
    CHANGE COLUMN price_per_kwh day_price_per_kwh DECIMAL(10,4) NULL DEFAULT NULL;

ALTER TABLE connector_status_snapshots
    ADD COLUMN night_price_text    VARCHAR(200)  NULL DEFAULT NULL AFTER day_price_per_kwh,
    ADD COLUMN night_price_per_kwh DECIMAL(10,4) NULL DEFAULT NULL AFTER night_price_text;
