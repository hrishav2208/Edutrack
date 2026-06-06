def patch_index():
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    new_section = '''
            <div id="admin-view-otp" class="app-section hidden">
                <div class="container">
                    <div class="page-header">
                        <h1>System Outbox (OTPs)</h1>
                        <p>Real-time view of securely generated login codes.</p>
                    </div>
                    <div class="card">
                        <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                            <h2 class="card-title" style="margin:0;">Active OTPs</h2>
                            <button class="btn btn-primary" onclick="renderOtpOutbox()"><i data-lucide="refresh-cw"></i> Refresh</button>
                        </div>
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>User Identifier</th>
                                        <th>Role</th>
                                        <th>OTP Code</th>
                                        <th>Expires At (UTC)</th>
                                    </tr>
                                </thead>
                                <tbody id="otpOutboxBody">
                                    <tr><td colspan="4" style="text-align: center;">Click refresh to load...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
'''
    if 'id="admin-view-campus"' in html and 'admin-view-otp' not in html:
        # We replace the first occurrence
        html = html.replace('<div id="admin-view-campus" class="app-section hidden">', new_section + '<div id="admin-view-campus" class="app-section hidden">', 1)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('Patched index.html with OTP Outbox')
    else:
        print('admin-view-campus not found or already patched')

if __name__ == '__main__':
    patch_index()
