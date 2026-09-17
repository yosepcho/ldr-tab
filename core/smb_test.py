from smb.SMBConnection import SMBConnection

def test_smb():
    conn = SMBConnection(
        "ldr",
        "Dustpno1!",
        "tablet",
        "server",
        use_ntlm_v2=True
    )

    conn.connect("10.29.10.40", 445)
    files = conn.listPath(
        "ldr",
        "/source_placement"
    )
    return [f.filename for f in files]