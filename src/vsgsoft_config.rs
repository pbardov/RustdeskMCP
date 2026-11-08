use hbb_common::config::{DEFAULT_LOCAL_SETTINGS, DEFAULT_SETTINGS};

pub fn apply() {
    crate::common::pre_global_init_app_name();
    let mut defaults = DEFAULT_SETTINGS.write().unwrap();
    for (key, value) in [
        ("custom-rendezvous-server", "rustdesk.vsgsoft.com"),
        ("relay-server", "rustdesk.vsgsoft.com:21117"),
        ("key", "sJXZyeSIrAefWzCALnclxsiNLsAjZ3p7Ke0G2OEFfYM="),
        ("api-server", ""),
    ] {
        defaults
            .entry(key.to_owned())
            .or_insert_with(|| value.to_owned());
    }
    drop(defaults);
    DEFAULT_LOCAL_SETTINGS
        .write()
        .unwrap()
        .entry("enable-check-update".to_owned())
        .or_insert_with(|| "N".to_owned());
}
