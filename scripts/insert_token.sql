DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tokens WHERE key = 'ZRZO6wGP-EkHBGLxq4KUt6YzFxX_0xiy_6SMJyigV7w') THEN
        INSERT INTO tokens (key, note, scopes, created_at, updated_at)
        VALUES (
            'ZRZO6wGP-EkHBGLxq4KUt6YzFxX_0xiy_6SMJyigV7w',
            'Arbiter phone app - infraction and player endpoints',
            'infraction,player',
            NOW() AT TIME ZONE 'utc',
            NOW() AT TIME ZONE 'utc'
        );
        RAISE NOTICE 'Token inserted.';
    ELSE
        UPDATE tokens
        SET scopes = 'infraction,player',
            note = 'Arbiter phone app - infraction and player endpoints',
            updated_at = NOW() AT TIME ZONE 'utc'
        WHERE key = 'ZRZO6wGP-EkHBGLxq4KUt6YzFxX_0xiy_6SMJyigV7w';
        RAISE NOTICE 'Token already existed - updated scopes.';
    END IF;
END
$$;
