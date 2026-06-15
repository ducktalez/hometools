package com.hometools.tv.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.tv.material3.Button
import androidx.tv.material3.Text

/**
 * First-run screen: the user enters the backend URL (e.g.
 * http://192.168.178.87:8011). Kept deliberately simple; a future version can
 * add mDNS discovery + a device token (see docs/IMPLEMENTATION_PLAN.md).
 *
 * NOTE: text entry on a TV is awkward. This scaffold uses a prefilled default;
 * a production version should add an IP-octet stepper or QR-pairing.
 */
@Composable
fun ServerSetupScreen(onConfirm: (String) -> Unit) {
    var url by remember { mutableStateOf("http://192.168.178.87:8011") }

    Column(
        modifier = Modifier.fillMaxSize().padding(64.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("hometools TV")
        Text("Server-Adresse: $url")
        Button(onClick = { onConfirm(url) }) {
            Text("Verbinden")
        }
    }
}

