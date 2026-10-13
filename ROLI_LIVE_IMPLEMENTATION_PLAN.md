# ROLI for Live: implementation and release plan

**Working repository name:** `roli-live`  
**Specification date:** September 18, 2026  
**Status:** implementation specification, not a tested implementation  
**Project identity:** an independent, community-maintained integration, not an official Ableton or ROLI product

## 1. Decision

Build **one installable controller integration**, consisting of a small Python MIDI Remote Script that runs inside Ableton Live and controls ROLI lighting over the existing USB connection. Keep performance MIDI on Live's native input path. Use stock hardware lighting commands wherever they meet the requirements. Add an original, bundled, lighting-only Littlefoot program only for hardware profiles that require it.

Do **not** make the new Ableton Extensions SDK, Max for Live, an external MIDI bridge, a background application, or ROLI Dashboard part of normal operation. Do not include an Extension merely to make the project sound like an Extension. The user-facing name should be **ROLI for Live**, with the technical description **control-surface integration**.

The intended result is: install once, connect a supported ROLI, open any Live Set, and have the keys follow Live's current scale and selected track color while native expression continues working.

There are two critical proofs before that promise can be advertised:

1. A clean Live installation must automatically discover and activate the integration, with the correct MIDI ports and MPE input configuration, without manual preference editing.
2. The specific keyboard and firmware must accept the required lighting control without losing native MIDI expression, permanently replacing its default program, or repeatedly writing settings to flash.

Neither proof has been completed in preparing this document. They are the first implementation gates, not assumptions to bury in a later installer task. If automatic activation is unavailable, a one-time guided manual setup is an explicitly labeled **assisted preview**, not fulfillment of the install-only target.

### Why this architecture

Ableton currently documents beta Extensions as run-once tools, not continuous MIDI or background performance systems. The documented beta also requires Suite. An Extension-only design would therefore add a requirement while failing to provide the persistent controller behavior. [S01], [S02]

Ableton supports Python 3 Remote Scripts installed in the User Library, outside individual Sets and outside the application installation. However, its documented third-party installation process still includes manually selecting the control surface and its ports. Script installation alone is not proof of automatic activation. [S03]

ROLI publishes an ISC-licensed BLOCKS API. Its protocol source explicitly recognizes the 49-key Piano, but a recognized model identifier is not proof that every documented lighting feature works on that model. This is a substantially better implementation starting point than copying unlicensed community scripts. [S10], [S11]

## 2. Product boundary

### 2.1 Required first release

The first release provides **Push-like scale and color guidance on a piano keyboard**, not a complete Push replacement.

| Area | First-release decision |
|---|---|
| Primary hardware target | ROLI Piano, 49 keys. Confirm the actual test unit before implementation. The owner's model has not been confirmed. |
| Additional hardware | Piano M and LUMI are separate profiles, admitted only after their own tests. Never infer support from the shared brand or protocol family. |
| Connection | One keyboard over USB. No Bluetooth, chained keyboards, Airwave, or DIN-only lighting control in version 1. |
| Host | Exact tested Live 12 builds. Target Standard and Suite without Max for Live; certify other editions only after testing. A beta is not required. |
| Operating systems | macOS and Windows, with exact OS versions and architectures listed in the release matrix. No blanket compatibility claims. |
| Musical context | The current scale displayed by Live and the selected track's color. No duplicate scale selector or per-track scale database. |
| Scale coverage | Every twelve-tone scale exposed by each supported Live build, using its actual interval set. |
| Keyboard behavior | Fixed piano pitches. Lighting guides the player; it does not quantize, transpose, filter, or remap their notes. |
| Expression | Preserve every MIDI expression dimension the tested device actually produces. Do not invent unsupported touch dimensions. |
| Daily workflow | No per-Set device, template, terminal, dashboard launch, or manual reconnection step. |
| Distribution | Free source and self-contained installer downloads. No project account, subscription, activation server, or telemetry. |

A changed model, firmware, OS, or Live version begins as **untested**, not automatically supported. Establish a small real compatibility matrix before expanding it.

### 2.2 Explicitly excluded from version 1

Do not implement a clip launcher, instrument browser, drum-pad layout, piano lessons, score following, automatic key detection, clip-playback note guidance, automatic plug-in configuration, or an elaborate settings window. Those are separate projects or later features.

Do not promise full Push performance routing. In version 1, **track selection drives lighting; Live's existing track arming, monitoring, and routing govern sound**. This avoids changing recording behavior just to illuminate a scale. Automatic selected-track playing focus is a separately gated enhancement in Section 13, not a hidden assumption in the core release.

Do not support arbitrary microtonal key mappings by pretending they are twelve-tone scales. Detect a mapping that cannot be represented reliably, use neutral lighting, and report the limitation.

## 3. Evidence and unresolved assumptions

All sources were reviewed on the specification date. References establish documented mechanisms; they do not replace tests in a licensed Live installation and on physical hardware.

| Topic | Established evidence | Still requires proof |
|---|---|---|
| Host scale state | The Live Object Model documents observable song root, scale intervals, scale name, and scale mode. [S04] | Equivalent properties and listeners are accessible from the selected Python Remote Script host versions. Max API documentation is not a Python API guarantee. |
| Selected track | Song View exposes selected track; Track exposes its color. [S05], [S06] | Listener lifecycle, Set replacement, deletion, and event ordering in the chosen host adapter. |
| Scale semantics | Live's Control Bar reflects the selected clip's scale settings. [S07] | Actual host snapshots for clip selection, empty slots, track-only selection, and different views. |
| Push visual convention | Push documents track-colored roots, white scale notes, green playing notes, and unlit out-of-scale notes in Chromatic mode. [S08] | Achievable LED appearance and non-invasive playing feedback on each ROLI profile. |
| Native MPE | Live supports MPE input and requires appropriate input and instrument configuration. [S09] | Automatic initial configuration and preservation during ROLI API/lighting operation. |
| Official ROLI protocol | The published source has model identities, configuration and program messages, and API-mode controls. [S11], [S12] | Actual firmware support, transport details, safe temporary operation, and acknowledgement behavior. |
| Lighting-only app | ROLI documents separate default touch and lighting handlers for LUMI. [S13], [S15] | Equivalent behavior on Piano 49, including local key callbacks while default MIDI remains enabled. |
| License suitability | The ROLI module carries ISC terms; its module header also declares JUCE dependencies. [S10], [S14] | File-by-file provenance and any separate build-tool dependency licenses. ISC does not relicense JUCE. |
| Vendor applications | ROLI describes a background hardware driver used by its software. [S18] | Direct operation without that application, and coexistence when it is installed. |
| Fully automatic install | No inspected public documentation establishes the required third-party activation mechanism. [S03] | Actual fresh-profile discovery, activation, Track/MPE configuration, and reconnection tests. |

## 4. Normative requirements

“MUST” is a release requirement. “SHOULD” is a preference that may be changed only in a recorded architecture decision. A blocked requirement must remain visible; an agent must not silently weaken it.

| ID | Requirement |
|---|---|
| R01 | One installer per supported platform installs the entire runtime. Users do not install Python, Node, JUCE, Max, a compiler, or a MIDI library. |
| R02 | After installation and any necessary Live restart, a supported device activates without manually selecting a control surface, choosing MIDI ports, or toggling input MPE. These actions are permitted only in an explicitly assisted preview. |
| R03 | Connection, disconnection, power cycling, USB port changes, sleep/wake, and Live/Set restarts recover automatically within the tested support matrix. |
| R04 | Lighting mirrors Live's effective scale mode, root, and interval set, plus the selected track's color. No guessed track key. |
| R05 | All physical keys map correctly through the device's supported octave and semitone transpose settings. Scale changes never alter emitted pitches. |
| R06 | Root, in-scale, out-of-scale, and physically held keys follow the visual rules in Section 5. A profile missing held-key feedback cannot claim full visual compliance. |
| R07 | Native notes, release behavior, MPE, pressure, pitch bend, and supported pedal messages remain intact. The integration never receives and re-emits performance MIDI as a replacement path. |
| R08 | The core integration does not change track arm, monitor, routing, clips, instruments, transport, or musical content. Selecting tracks changes lighting, not recording policy. |
| R09 | Lighting updates are temporary. They do not repeatedly write flash, replace factory firmware, save a custom program as the permanent default, or reset the keyboard. |
| R10 | Exit, connection loss, and faults leave the keyboard playable and provide a tested path back to native lighting. Existing user settings are preserved or explicitly restored. |
| R11 | The runtime uses Live's available Python facilities and host services only. No persistent external process, virtual MIDI port, polling web service, or network access. |
| R12 | Every redistributed component has a verified license and recorded provenance. Original project code is MIT; retained upstream notices remain intact. |
| R13 | The installer supports safe upgrade, rollback, repair, and uninstall without modifying unrelated files or opaque Live preferences. |
| R14 | Diagnostics identify unsupported conditions without recording performances, collecting personal data, or producing repeated pop-ups. |
| R15 | Public compatibility and plug-and-play claims match physical tests, not mocks or architectural intent. |

## 5. Exact user-visible behavior

### 5.1 Source of truth

Read the current host scale state as one coherent snapshot: scale enabled, root, interval set, and selected track color. Prefer the observable Song values after the host has settled the current selection. Use clip/selection notifications to refresh that snapshot, not to invent a competing precedence system.

The current Live manual says the Control Bar reflects the selected clip. Consequently, selecting a track does not inherently mean that the track owns a separate permanent key. [S07] The product follows **what Live currently displays**, including a newly selected clip's scale when Live adopts it. It does not automatically follow a different clip merely because that clip is playing.

Before implementation, capture expected snapshots for: track-only selection, a selected MIDI clip, a selected audio clip, an empty clip slot, multiple selected clips, Session View, Arrangement View, and a pinned or previously displayed detail clip. Resolve differences from the actual host rather than hard-coding a guessed “global versus track” priority.

### 5.2 Lighting policy

The following policy is the project's specification. Semantic resemblance to Push is the goal; identical perceived RGB output across different LED hardware is not promised.

| State | Required display |
|---|---|
| Scale enabled | Root keys use the selected track color; other scale keys are white; out-of-scale keys are off. |
| Scale disabled | All available keys use dim neutral white; there is no root emphasis. |
| Key physically held | Green overlays the background. On release, restore the current background, not the background from when the key was pressed. |
| Sustain pedal held after key release | Restore that key's background. This is a physical-playing indicator, not an estimate of whether the instrument is still sounding. |
| Pitch bend or pressure | Do not move the illuminated physical key to a different pitch. Do not flood the host with lighting changes for every expression sample. |
| Track color changes | Recolor roots immediately after the next coherent host snapshot. |
| Audio, group, return, or main track selected | Continue displaying Live's effective scale and the selected track color when available; never arm or reroute anything. |
| No valid selected color | Use a documented neutral root accent. |
| Unsupported tuning or uncertain physical mapping | Neutral lighting plus one diagnostic message. Never show a confidently wrong scale. |
| Host disconnect or control fault | Relinquish custom lighting according to the tested device recovery procedure; retain native playing. |

For a physical key whose emitted base MIDI note is `n`, root `r`, and set of scale offsets `I`, membership is determined by **(n - r) modulo 12 belonging to I**. This is an algorithm definition, not a dependency on a music-theory library. Normalize intervals once; do not map scale names to a hard-coded seven-note list.

Use the hardware's actual emitted-note mapping, including its octave and semitone transpose controls. Do not infer note numbers from labels such as C3/C4. Do not compensate for arbitrary MIDI effects or transposition inside an instrument; those are downstream of this integration's defined view of the keyboard.

### 5.3 Brightness and color

Provide one fixed default palette and one optional master brightness setting. Default to the user's existing readable brightness; use a profile-tested moderate fallback only when it cannot be read. Calibration and RGB conversion belong in the hardware profile, not in scattered color constants.

Choose a documented luminance floor for dark track colors so roots remain visible. Apply the same rule consistently. A green track color may resemble the playing overlay; do not misrepresent that as uniquely distinguishable. Test representative dark, bright, and saturated track colors.

No animated transitions or color editor in version 1. They add traffic and maintenance without solving the core problem.

### 5.4 MPE setup and preservation

Preserving existing MPE is different from configuring a factory-new keyboard and a new Live preference profile. Test both.

When the device is already configured correctly, do not rewrite its expression settings. For a new setup, the installer may present one clear consent step describing proposed hardware MPE changes. Apply only verified settings needed for the chosen profile, once, with a saved before-state and a restore action. Do not silently change pressure curves, channel ranges, pedal assignment, or pitch-bend range on every connection.

Host Track/MPE configuration is part of the automatic-activation gate. Instrument capability remains the user's musical choice: the project cannot make a non-MPE instrument expressive. Document one tested reference instrument and preset per certified Live edition, with matching bend range, for a reproducible sound check. Do not install that instrument into existing Sets or alter arbitrary plug-ins. [S09]

## 6. Architecture and component contracts

### 6.1 Two independent paths

**Performance:** keyboard native MIDI output -> Live native MIDI input -> existing track/instrument routing.

**Lighting:** observable Live state -> controller logic -> approved ROLI protocol messages -> hardware lighting.

Control-surface registration must not swallow the notes or expression messages needed by tracks. Do not assume that receiving a MIDI message in a script proves non-consuming observation. Verify forwarding behavior in the host.

Prefer local hardware key-state feedback for the green overlay, if it can coexist with default MIDI handling. Otherwise, investigate a host-supported non-consuming observation path. If neither is available, do not replace native MIDI just to obtain green keys. Record the feature as blocked and keep that profile out of full visual certification.

### 6.2 Minimal runtime layout

These are proposed files to create during implementation, not code supplied by this document.

| Component | Responsibility |
|---|---|
| `ROLI_Live/__init__.py` | Host entry point and verified device-discovery metadata. |
| `surface.py` | Lifecycle and wiring only. No scale or protocol logic. |
| `live_adapter.py` | Host-specific reads, listeners, scheduling, and output transport. All version-sensitive host access stays here. |
| `state.py` | Immutable logical snapshots, scale membership, and required output state. Testable outside Live. |
| `colors.py` | Palette and brightness conversion. |
| `roli_protocol.py` | Bounded parsing, framing, approved commands, and acknowledgements. No vendor application dependency. |
| `device_profiles.py` | Verified model/firmware capabilities, geometry, mapping, and recovery policy. |
| `session.py` | Discovery, initialization, ownership, restore, retry, and reconnect state machine. |
| `assets/` | Only original, reproducibly built lighting programs required by supported profiles, plus manifests and notices. |

Do not add a generic plug-in framework, configuration server, third-party MIDI abstraction, or dynamically downloaded driver. Use the Python version actually embedded in the oldest certified Live build, not the developer's system Python version.

### 6.3 Internal data contracts

**Live snapshot:** schema version, generation number, scale-enabled flag, root 0 through 11, normalized interval set, selected-track identity valid within this Set, track RGB, and tuning-validity status. Scale name is diagnostic only.

**Device profile:** model identifier, observed USB identifiers and MIDI port patterns, verified firmware range or explicit versions, physical key geometry, default note mapping and supported offsets, available transport, stock-lighting or receiver strategy, native expression capabilities, and tested recovery behavior. Never insert guessed IDs or use the first port containing “ROLI.”

**Lighting state:** schema version, generation number, scale mask, root, palette, brightness, physical mapping revision, and any non-invasive held-key state. For the receiver path, send complete logical state at initialization and recover with a complete state after loss. Do not require a perpetual per-key animation stream.

**Session record:** device identity scoped locally, session generation, pre-session temporary settings, explicitly authorized persistent setup changes, ownership status, and last acknowledged lighting generation. Do not log MIDI notes or store a user's performance.

### 6.4 Lifecycle

Use the explicit states **Disconnected, Probing, Verified, Initializing, Active, Suspended, Restoring, MIDI-only**.

A device must be identified before model-specific writes. Initialization is idempotent. Detaching invalidates queued work, listeners, and acknowledgements from the old session. Reconnection starts with fresh identification and a new full host snapshot, not stale port handles or remembered topology addresses.

Coalesce related host notifications and keep only the latest pending lighting state. Run host-object access on the host-supported execution context. Never block it with sleeps, synchronous retry loops, or background threads touching Live objects.

Use periodic work only for protocol liveness where required. The official protocol defines an API ping timeout; its actual firmware behavior must be measured before choosing a heartbeat. Keep control traffic bounded and stop it when the device is absent. [S11]

On an uncertain ownership conflict with another application, suspend writes and explain the conflict. Never kill a vendor process, uninstall its driver, or continuously fight another lighting client.

## 7. Feasibility gates: complete these before building the full product

Each gate produces a short report, reproducible steps, captured evidence, and a PASS or BLOCKED result. An agent without the required hardware or licensed host must mark the corresponding tests **NOT RUN**. Simulated tests cannot promote a hardware profile to supported.

### G0. Inventory and provenance

Obtain one physical primary-target unit and a licensed Live installation. Record the model, firmware, OS, architecture, Live build and edition, embedded Python version, USB identifiers, and actual MIDI endpoints. Record whether vendor software is installed.

Pin an exact commit of the official ROLI repository. Inventory the license of every file considered for reuse, including transitive build inputs. Preserve a small, attributable source manifest. Do not copy community code while waiting for this review.

**Pass:** the team can reproduce the baseline environment and identify the exact source rights. **Blocked:** no physical test unit, unidentified model, or unclear rights for a necessary component.

### G1. Prove Live access and automatic activation first

Create the smallest development-only probe needed to test host integration. It must establish:

1. Reads and listeners for effective scale state and selected-track color work in the actual Python host, including Set replacement.
2. A script can exchange the required control messages with the correct device endpoint without consuming performance MIDI.
3. Live can discover and instantiate the third-party script from installed capability metadata on a fresh preference profile. Investigate the host's actual capability mechanism, commonly exposed by control-surface entry points such as `get_capabilities`; do not assume a name alone provides auto-loading.
4. The performance input, Track input setting, and MPE input setting can be correctly established through a supported activation mechanism, or already come from verified automatic host behavior.
5. Reconnection works without a manual control-surface selection, and existing controllers are not displaced.

Test a fresh user profile with the keyboard initially absent and initially connected. Repeat with relocated User Libraries and existing controller assignments. Installing a folder and observing it in the dropdown is **not** sufficient evidence.

**Pass:** all five outcomes have reproducible evidence for each intended host/OS combination.

**If blocked:** finish an assisted development preview if useful, but do not build an installer that secretly patches undocumented preferences to pretend the gate passed. Record the unsupported operation and ask Ableton for a supported third-party discovery/configuration mechanism or integration route. A revised host release can be retested later. The strict release remains blocked until an approved mechanism exists.

**Forbidden shortcuts:** editing opaque `Preferences.cfg` data, decompiling and repackaging Ableton controllers, impersonating Push, modifying Live's application bundle, adding undocumented `Options.txt` switches as a dependency, or driving the preferences UI with fragile screen automation.

### G2. Prove safe direct hardware control

First capture baseline MIDI behavior with no custom lighting. Then identify the keyboard, read necessary configuration, and change one harmless lighting setting through Live's control output. Restore it. Repeat while playing independent expressive notes and using a pedal.

Test without ROLI Connect, Dashboard, or the ROLI Hardware Driver running. Also test a machine where those applications are installed. Establish whether transport contention is real, which endpoint is affected, and whether normal coexistence is possible. Vendor application availability is not a project runtime dependency. [S18]

Determine whether API mode changes native MIDI behavior. Read back configuration where possible and power-cycle after temporary changes to test persistence. Do not infer “RAM only” from a setting name or an apparently successful command.

**Pass:** direct control, verified identity, expression preservation, and reversible temporary changes. **Blocked:** unavoidable vendor daemon, lost native MIDI, unknown persistence, or unexplained device resets.

### G3. Choose exactly one lighting strategy per hardware profile

**First choice: stock configuration.** Test the official configuration mechanisms for root, scale, colors, brightness, and mode behavior. Compare every supported Live interval set against what the keyboard actually illuminates. A shared scale name is not enough. Test green held-key feedback and octave/transpose behavior too. The SDK provides relevant configuration identifiers, but their model-specific implementation must be verified. [S12], [S16]

Accept this strategy only if it meets the complete visual contract with temporary writes. Do not ship a limited list of stock scales while claiming all Live scales work.

**Second choice: original lighting-only receiver.** If stock configuration fails, use a small original Littlefoot program that preserves the default touch/MIDI handler and replaces only lighting. Verify the documented separate-handler mechanism on this firmware; its LUMI documentation does not prove Piano behavior. [S13], [S15]

The receiver must accept a twelve-bit scale mask, root, colors, brightness, and mapping state through a versioned control protocol. It must retain native playing, mode/octave controls, and supported pedals. Verify whether local key callbacks are still delivered with default touch handling enabled. Do not copy a program that switches off native touch handling and generates replacement note messages.

**Pass:** one selected strategy achieves the entire profile contract. **Blocked:** neither strategy preserves native behavior. Do not create a third architecture with an always-running MIDI translator merely to hide the failure.

### G4. Prove deployment, restoration, and build rights

For the stock path, verify snapshot/restore and temporary writes, including crash and power-loss behavior.

For the receiver path, prove that the project can compile its own source, upload it automatically through the control connection, verify the loaded version, and return to native behavior. Prefer a transient program loaded into RAM when Live attaches. Do not require users to drag a file into Dashboard, overwrite a factory default, or download an untracked binary.

The official Littlefoot compiler source is an implementation reference, but it uses JUCE types. Audit the exact build dependency set instead of assuming the ISC module is standalone. A build-only dependency is still part of the provenance review. [S14], [S21]

**Pass:** reproducible receiver bytes where needed, approved toolchain, no unlicensed embedded runtime, and tested recovery without saving a new default program. **Blocked:** unknown binary provenance, required paid proprietary build component, unavoidable persistent replacement, or no reliable recovery.

Do not turn this task into a fresh compiler project. First test an audited existing build toolchain. A substantial portability rewrite requires an explicit architecture decision and must not be concealed inside “minimal integration.”

## 8. Hardware protocol and safety specification

### 8.1 Implement only the needed protocol subset

Port or implement the smallest necessary framing, packing, checksum, acknowledgement, configuration, and transient program-transfer operations from verified official sources. Preserve notices when adapting code. Do not ship the complete C++ SDK just to send several messages.

Before production writes, create `protocol.md` with exact, observed request/response layouts, field widths, maximum packet lengths, byte order, checksum rules, addressing, acknowledgement counters, retry behavior, and firmware exceptions. These details must come from pinned source and test captures, not guessed hex strings.

The official protocol distinguishes a dynamic topology index from a stable device identity. Discover the current address on connection; never copy a hard-coded topology byte from a sample capture. [S11]

Use read-only identity requests for discovery. Reject unknown identities and unsupported firmware before profile-specific writes. Do not probe random SysEx commands, broadcast mutations, accept arbitrary uploaded payloads from a network, or send configuration to every connected ROLI product.

Production command permissions must be explicit. Allow only the tested identity/configuration reads, temporary lighting operations, required liveness operations, restore operations, and optional transient receiver upload. **Exclude firmware updates, factory resets, device renaming, permanent default-program saves, and unrelated musical configuration.** Separately authorize any one-time MPE onboarding changes.

### 8.2 Temporary state and restore

Keep a before-state for each modified setting and record its last value written by this integration. On normal release, restore only settings still owned by this session. Do not overwrite a newer user change made in another application.

Never enable automatic transposition to the selected key. Never change MIDI port forwarding, throttling, expression sensitivity, or unrelated mode settings as an undocumented side effect. ROLI's configuration list exposes these controls separately; their presence is not permission to modify them. [S12]

No real-time scale, color, brightness, or track update may cause flash persistence. Include a measured check for this, not only a code search for a save flag. One-time consented MPE setup is a separate transaction, not part of the lighting update loop.

The project does not ship factory firmware or a factory Littlefoot program extracted from Dashboard. Recovery should relinquish the temporary program or restore settings through tested native mechanisms. Official reset instructions belong only in last-resort troubleshooting with a clear warning that user settings may be lost, never in automatic operation. [S17]

### 8.3 Receiver protocol, only if G3 selects it

Define a versioned, bounded message format after confirming the physical transport limits. Include schema version, message type, session/generation value, payload bounds, and acknowledgement behavior. Define initialization, complete state, state acknowledgement, liveness, release, and diagnostic status. Reuse the official program-event or shared-data transport rather than reserving musical note pitches as lighting commands.

Commit complete state atomically on the device, so a root update cannot briefly combine with the old scale mask. Ignore old generations. A restart or missing-state condition requests or receives a full state rather than an unbounded sequence of missed deltas.

Local repainting and physical key feedback must not emit musical notes. A watchdog must return to a proven playable/native-lighting state when host ownership expires. An actual hardware test must establish what API timeout and program exit do; source constants alone are insufficient.

## 9. Install, upgrade, and uninstall

### 9.1 Supported installer experience

The public release provides one self-contained installer download for each certified platform. The developer archive is not the normal install path.

Use small OS-native installer wrappers around a common versioned payload manifest. Prefer Swift with system UI/filesystem APIs on macOS and native Windows APIs for the Windows wrapper. Avoid Electron, a bundled browser, or a separate installed scripting runtime. The wrappers perform setup only and exit; the musical integration remains Python inside Live.

Keep installer logic limited to environment checks, directory selection, file transactions, activation validation, and recovery. Do not build a general package manager. Source code for the installer is part of the open-source project.

Required install sequence:

1. Detect supported Live installations and explain unsupported versions without modifying them. Locate the actual User Library, including custom, external, localized, or cloud-synced locations. If it cannot be established reliably, use one folder picker during installation rather than guessing.
2. Detect a running Live process. Ask the user to close it when required; never kill it or risk an unsaved Set.
3. Display the installation destination, required permissions, and any proposed one-time hardware configuration. Preserve existing settings by default.
4. Stage the complete payload, validate its manifest and hashes, and atomically install one stable `ROLI_Live` directory under the actual User Library's `Remote Scripts` directory. Do not create a new controller folder for each release.
5. Apply only the automatic-activation mechanism proven by G1. Do not invent an API for registering a control surface or enabling MPE.
6. Let Live load the integration and record a local version/health receipt. If Live has not yet run or the keyboard is absent, report **installed, connection not yet verified**, not **working**.
7. On the first supported connection, initialize the profile, display current lighting, and record successful verification. This must require no terminal commands, file copying, vendor application, or manual MIDI preference setup in the strict release.

The official User Library script location is suitable for persistence across application updates, but the installer must resolve the user's real path rather than relying exclusively on platform defaults. [S03]

### 9.2 Signing and trust

Sign and notarize the macOS release installer. Sign the Windows executable. Publish checksums, versioned sources, build provenance, and third-party notices next to the downloads. Apple checks developer identity/notarization, while Windows also considers reputation; a signature must not be advertised as a guarantee that every security warning disappears. [S24], [S25]

Do not instruct users to disable Gatekeeper, antivirus, or system-wide security. Signing credentials and associated release costs are maintainer operations, not hidden runtime subscriptions for users. Keep signing secrets out of pull-request builds.

### 9.3 Upgrade and rollback

An upgrade preserves the stable installation path and any minimal user preferences, stops safely when Live is running, replaces only owned files, and can restore the previous complete payload after failure. Schema migrations are versioned and reversible. A firmware/profile mismatch discovered after upgrade disables writes rather than experimenting on the keyboard.

No automatic updater or daily update check in version 1. Users rerun the newer signed installer. The prior verified release remains available. Where reproducibility is tested, compare unsigned payloads before platform signing changes the distributed package.

### 9.4 Uninstall and repair

The same installer supports repair and removal. Remove only files listed as project-owned; preserve user-modified files or ask before removal. Do not delete the User Library, rewrite unrelated preferences, reset a device, or remove vendor software.

Restore explicitly changed hardware setup settings only through a user-requested restore action with device identity verified. Explain that installing or uninstalling while the keyboard is disconnected cannot verify its current state. A temporary receiver must return to native operation by the recovery behavior already tested in G4.

The assisted preview may explain how to clear a manually selected script entry. The strict release must test removal against its actual automatic discovery mechanism and leave no recurring error dialog.

## 10. Open-source and dependency policy

License original controller code, receiver source, installer source, tests, and project documentation under MIT. Keep the original ISC notices with adapted ROLI code. Add `LICENSE`, `THIRD_PARTY_NOTICES.md`, a license directory, and a dependency/provenance manifest. These files are implementation deliverables; this specification itself remains one Markdown file. [S10], [S23]

| Material | Policy |
|---|---|
| Original project work | MIT with contributor attribution. |
| Verified ISC ROLI files | Reuse only necessary portions, pin a commit, retain copyright/license text, and record adaptations. |
| Ableton host modules | Use only as available in the user's licensed Live installation under applicable terms. Do not bundle, decompile, or republish them. |
| Community code with no verified license | Do not copy, translate, vendor, or distribute it. Public visibility is not a reuse license. [S19] |
| Factory software, firmware, presets, logos, and Dashboard-extracted programs | Do not include them. Use original assets and link to official support when necessary. |
| Runtime dependencies | Target zero external packages. Any exception needs a recorded reason and license approval before introduction. |
| Build/test tools | Pin versions and review their licenses separately. Conventional open-source build tooling is not automatically forbidden, but any obligations and embedded output material must be understood. |
| JUCE | Do not assume the ROLI module's ISC terms cover JUCE. No JUCE runtime in the end-user integration. Approve any conditional build-only use separately. [S14], [S21] |
| Generated receiver binary | Include its original source, exact compiler/toolchain manifest, license provenance, build instructions, and reproducible hash. No unexplained blob. |

The community `LUMI-lights` repository is useful evidence that experimentation exists, but no usable project license was verified during this review. Its README also discusses a factory program extracted from Dashboard. Neither that program nor the repository's code is an approved project input. Use the official licensed implementation sources instead. [S20]

For every adopted source file, record upstream URL, exact commit, path, SPDX license where applicable, copyright, purpose, local modifications, and whether it enters runtime, build tooling, or documentation. A license scan supplements this review; it does not replace it.

Use an ordinary contribution workflow with a sign-off/provenance declaration. Contributors must not submit copied vendor resources or license-unknown snippets. No proprietary contributor agreement is necessary for the proposed model. Preserve independent-project branding and avoid implying vendor certification.

## 11. Ordered implementation work packages

Execute in this order. Do not spend substantial effort on installers or additional models before the primary transport and automatic-activation gates are resolved. Each package should be one reviewable milestone, not a single enormous generated change.

| Package | Dependency | Required work and deliverables | Completion condition |
|---|---|---|---|
| P01: baseline | None | Complete G0. Create the repository skeleton, license/provenance register, exact environment inventory, and a native MIDI baseline recording/report. | Model and source rights are identified; tests can be repeated. |
| P02: host proof | P01 | Complete G1. Record actual Python listeners and transport entry points, capability discovery, the exact input/output port matrix, and automatic Track/MPE behavior. | Strict activation passes, or a precise blocked report explicitly limits work to preview status. |
| P03: hardware proof | P01; P02 transport | Complete G2 and G3. Capture read-only identification and a reversible lighting transaction; compare stock and receiver paths against the same visual/MPE tests. | One justified strategy is selected per initial profile. |
| P04: deployment proof | P03 | Complete G4. Approve tooling and recovery. If a receiver is needed, create the smallest original receiver and reproducible build path before broader controller features. | Safe attach, native playing, detach, and crash recovery demonstrated. |
| P05: pure core | P02 and P03 | Implement logical snapshots, masks, mapping, palette, bounded protocol parsing, and session transitions. Use fixtures, including malformed and reordered input. | Deterministic tests pass without Live or a keyboard. |
| P06: Live integration | P04 and P05 | Connect listeners, transport, full-state resynchronization, held-key feedback, error containment, and local diagnostics. Exercise new/opened Sets and track deletion. | Core hardware acceptance tests pass with no project edits or note-path regression. |
| P07: installation | Strict G1 pass; P06 | Build native installers, stable payload manifest, signed packaging, repair, atomic upgrade, rollback, and uninstall. Implement the proven activation mechanism only. | Fresh-machine install works without developer tools or vendor utilities. |
| P08: certification | P07 | Run the full matrix below. Collect hardware reports from more than one user environment, documenting exact versions. Add a second model only as an independent profile. | Every advertised combination has physical evidence and no unresolved release blocker. |
| P09: public release | P08 | Publish source, tagged artifacts, notices, checksums, build provenance, compatibility table, setup/recovery instructions, and issue templates. | An independent enthusiast installs from the release download without developer help. |

Parallel work is permitted only where dependencies allow it. For example, provenance and pure mapping fixtures can be prepared while hardware is being obtained, but their completion does not substitute for physical tests.

### Required repository outputs

Keep the repository understandable: runtime source, conditional receiver source/build tooling, platform installer wrappers, automated tests, hardware test reports, protocol documentation, a compatibility manifest, and standard project/license documents.

`README.md` should state what works, exact compatibility, the normal install path, and the known limits before any promotional text. `CONTRIBUTING.md` should explain source provenance and hardware-test requirements. Issue forms should request model, firmware, OS, Live build, installation tier, and a redacted diagnostic report, never a full performance recording by default.

The compatibility manifest is the source of truth for both release notes and profile admission. A claim must not appear only in prose while runtime code enables an untested profile.

## 12. Acceptance tests and release evidence

### 12.1 Required tests

| Test | Procedure | Pass criterion |
|---|---|---|
| A01: clean install | Install on a fresh certified OS user profile with Live, but no development tools or running vendor utilities. Test keyboard absent and present. | One installer; automatic first connection; no preferences, scripts, terminal, or account steps. |
| A02: existing environment | Install with another controller configured, custom User Library, and existing Sets. | No displaced controller, lost preferences, or modified musical content. |
| A03: restart/reconnect | Perform 20 cold starts and 100 disconnect/reconnect cycles, including another USB port and supported sleep/wake sequences. | No manual repair, stale addressing, duplicate instance, or persistent wrong display. |
| A04: all scales | Enumerate actual interval sets from the certified host build; test each with all 12 roots across the keyboard. | Physical lighting matches computed membership. No major/minor-only substitute. |
| A05: context changes | Select differently scaled clips, empty slots, and tracks; include Session, Arrangement, and an audio clip. | The display follows Live's current visible scale, not a guessed per-track or playing-clip scale. |
| A06: colors | Change track colors and select audio/group/return/main tracks. Include very dark colors. | Roots use the defined conversion; no stuck old color or routing side effect. |
| A07: scale off and unsupported tuning | Disable scale mode; then load a tuning/mapping outside the implemented contract. | Defined neutral display; unsupported case diagnosed once; no misleading scale. |
| A08: octave and transpose | Exercise every supported octave/semitone offset and both range extremes. | Correct physical mapping; no off-by-one or octave-name error; emitted pitches unchanged by lighting. |
| A09: held keys | Hold several keys, change scale/color, release in varied orders, and repeat with pedal held. | Green while physically held; correct current background after release; no stuck overlay. |
| A10: MPE fidelity | Compare native and integrated operation using a reference instrument; bend and press individual notes within held chords. Test soft/hard attacks and supported release/pedal data. | Independent expression preserved; no flattened channel assignment or dropped dimension. |
| A11: event integrity | Run at least 100,000 generated MIDI events through development fixtures, plus physical expressive recording tests. | No missing/duplicated notes, channel rewriting, control leakage, or stuck notes attributable to integration. |
| A12: native controls | Use mode, octave, power, and supported pedal controls during a session. | Native behavior remains available; integration does not forcibly undo deliberate user changes. |
| A13: no project mutation | Run lighting tests on an unsaved blank Set and a populated Set; inspect undo/dirty state. | No dirty Set, undo pollution, changed arming/routing, or altered musical content caused by the core. |
| A14: persistence | Change scales/colors repeatedly, quit, power-cycle, and inspect device state and captured writes. | No runtime flash writes or permanent default-program replacement; expected restore behavior. |
| A15: failure recovery | Interrupt initialization/upload, stop Live unexpectedly, unplug during a transaction, and simulate lost acknowledgements. | Device remains playable; bounded retries; tested native-lighting recovery; no reset loop. |
| A16: ownership | Open/close vendor control software and test another active MIDI client where supported. | Coexistence or clear suspension; no process termination, tug-of-war, or musical disruption caused by lighting. |
| A17: unknown device | Attach another MIDI device, an unsupported ROLI model, and unverified firmware. | No profile-specific writes; no fake compatibility claim; native MIDI remains available. |
| A18: parser/queue abuse | Feed truncated, oversized, foreign, duplicate, and out-of-order frames to the test adapter. | Bounded work/memory, safe rejection, no arbitrary device operation. |
| A19: performance soak | Run two hours of use, including 30 minutes of dense expressive playing and 1,000 track/scale changes. | No attributable audio dropouts, growing queue, accumulating listeners, or sustained resource leak. |
| A20: lifecycle | Open, close, and replace Sets; delete selected tracks; disconnect during shutdown. | No stale host object use or reconnecting to an old Set's state. |
| A21: upgrade/rollback | Upgrade an older release, interrupt installation, repair, and restore the previous version. | Atomic complete payloads; settings retained; no half-installed controller. |
| A22: uninstall | Remove with the keyboard connected and absent; reopen Live afterward. | Only owned files removed; no recurring script errors; recovery status reported honestly. |
| A23: reproducibility/licenses | Rebuild unsigned payloads from tagged source and inspect all shipped files. | Matching deterministic assets, complete provenance/notices, no unapproved vendor or community material. |
| A24: offline/privacy | Install and operate offline after required host licensing; inspect outbound behavior and exported diagnostics. | No project network dependency or telemetry; no performance data, raw serials, or personal paths in default exports. |

For Piano 49, account for the documented Adaptive Press behavior when comparing hard and soft strikes. Do not report normal baseline pressure behavior as a lighting regression or attempt to “fix” it in MIDI translation. [S22]

### 12.2 Measurable engineering targets

These are proposed acceptance targets, not measured results.

For a normal, non-overloaded certified host, target **200 ms or less at the 95th percentile** from host state-change notification to visibly settled scale lighting, with no ordinary test case exceeding 500 ms. Record the measurement method and distinguish device acknowledgement from observed light output.

Target restoration of the current scale within **3 seconds after the host exposes the reconnected endpoint**. Do not count operating-system device enumeration delay as if it were script processing, and report total observed user delay separately.

Do not place Python work in the performance-note path. Benchmark the same audio configuration with integration on and off, report latency/jitter measurements, and reject attributable dropouts or material regression. Do not advertise mathematically zero latency just because notes are not intentionally retransmitted.

No polling of Live's UI scale state when reliable listeners exist. No repeated full-state output while nothing changes. A required heartbeat is separate from a lighting refresh and must stay within the profile's tested rate budget.

### 12.3 Requirement traceability

| Requirements | Main work packages | Required evidence |
|---|---|---|
| R01, R02 | P02, P07 | A01, A02 |
| R03 | P06, P08 | A03, A15, A20 |
| R04, R05, R06 | P03 through P06 | A04 through A09, A12 |
| R07, R08 | P02, P03, P06 | A10, A11, A13, A19 |
| R09, R10 | P04, P06 | A14 through A17, A22 |
| R11, R14 | P06 through P08 | A16, A18, A19, A24 |
| R12 | P01, P04, P09 | A23 |
| R13 | P07 | A21, A22 |
| R15 | P08, P09 | Published matrix and linked test reports for every supported combination |

Software CI should test pure logic, protocol fixtures, packaging manifests, and licenses on every change. Physical tests run in a controlled local lab or a manually triggered hardware environment. Do not execute untrusted pull-request code on a runner with a connected keyboard or signing credentials.

## 13. Enhancements that must not delay the minimal release

**Selected-track playing focus:** investigate only after the lighting core works. The current Track API documents `implicit_arm`, but this does not establish a safe third-party controller policy or identical Python access. [S06] A future enhancement must preserve manual arm states, recording, held-note release, pedal behavior, other controllers, and the user's routing. It must not merely arm each selected track and disarm everything else. Without those proofs, retain normal Live routing and say so.

**Practice-note playback:** a later feature may illuminate notes from a dedicated guide source. It needs a real note-event delivery mechanism, separation from the user's performance, and clear transport/stop behavior. Do not infer note events from clip metadata polling or mistake the Extensions SDK for a real-time MIDI callback system.

**Optional Extension interface:** reconsider only if a future documented SDK meaningfully improves setup or diagnostics. It must not become necessary to use the controller, add Suite-only requirements to the core, or duplicate the controller's scale logic.

**Additional devices or transports:** add profiles only with independent protocol, mapping, MPE, and recovery tests. Shared brand names are not a compatibility test.

## 14. Release decision and agent execution rules

Use these publication labels consistently:

| Label | Meaning |
|---|---|
| Experimental | Research implementation. Some hardware/host behavior remains unverified. No plug-and-play claim. |
| Assisted preview | Functional on explicitly tested configurations, but initial manual Live preference or device setup is required. Not completion of the install-only requirement. |
| Install-once release | R01 through R15 passed for every advertised configuration. No manual controller/port/MPE setup and no per-Set work. |

A strict release cannot be obtained by renaming manual setup “installation,” limiting tests to an already configured developer machine, or shipping undocumented preference edits. Likewise, colorful keys do not compensate for broken MPE.

For every milestone, the implementing agent must report changed files, tests run, actual environments, test results, open blockers, and the next specific experiment. It must distinguish NOT RUN from PASS. All hardware IDs, firmware ranges, API entry points, and packet fixtures must come from observed evidence or pinned primary source, never from plausible guesses.

When a gate is blocked, preserve the working components and state the exact unresolved dependency. Do not expand scope to an unrelated daemon, replace native MIDI, copy license-unknown code, or announce compatibility without evidence.

**First task for the implementing agent:** complete P01, then prove P02 on a clean Live profile. The scale renderer is straightforward compared with automatic host activation and safe hardware ownership. Resolve those first.

## 15. Sources

These references support the documented facts in this plan. Architectural choices, requirements, proposed performance targets, and work packages are project decisions. Pin exact upstream revisions during P01 because documentation and repository branches can change.

**S01.** [Ableton Extensions FAQ][S01]. Current beta eligibility, run-once behavior, and real-time limitations.

**S02.** [Ableton Extensions SDK landing page][S02]. Public beta SDK entry point; the complete downloaded SDK was not inspected for this specification.

**S03.** [Installing third-party remote scripts][S03]. Python version transition, User Library location, and documented manual selection of surface and ports.

**S04.** [Live Object Model: Song][S04]. Observable root, scale intervals, scale mode, and tuning state. This is LOM documentation, not proof of Python surface access.

**S05.** [Live Object Model: Song View][S05]. Selected track and detail-clip context.

**S06.** [Live Object Model: Track][S06]. Track color and the documented implicit-arm property.

**S07.** [Live 12 manual: Live Concepts, Control Bar][S07]. Relationship between displayed scale settings and selected clips/slots.

**S08.** [Push manual][S08]. Chromatic scale layout and documented note/root/playing color conventions.

**S09.** [MPE in Live FAQ][S09]. MPE input setup, supported use, and instrument considerations.

**S10.** [ROLI BLOCKS API license][S10]. ISC permission and notice obligations.

**S11.** [ROLI BLOCKS protocol definitions][S11]. Piano 49 identity recognition, topology addressing, command families, and API liveness definitions.

**S12.** [ROLI configuration identifiers][S12]. MIDI, MPE, scale, color, brightness, transpose, and mode configuration names.

**S13.** [ROLI Littlefoot function documentation][S13]. Separate default touch/lighting handling and local configuration interfaces, documented for LUMI where specified.

**S14.** [ROLI module declaration][S14]. Module license and JUCE dependency declarations.

**S15.** [ROLI engineer discussion: controlling LUMI with the BLOCKS API][S15]. Firsthand explanation of MIDI-preserving custom lighting on LUMI; not a Piano 49 certification.

**S16.** [Using Piano M with ROLI Dashboard][S16]. Model-specific lighting, mode, mapping, and expression controls.

**S17.** [ROLI Piano FAQs][S17]. Piano hardware and official support/recovery information.

**S18.** [What is the ROLI Hardware Driver?][S18]. Role of the vendor's background application.

**S19.** [GitHub: licensing a repository][S19]. Why public source without a license is not automatically available for reuse.

**S20.** [Community LUMI-lights repository][S20]. Reviewed as background only; not approved as a code or factory-program source for this project.

**S21.** [ROLI Littlefoot compiler source][S21]. Compiler implementation and dependency review starting point.

**S22.** [Understanding Press/Aftertouch on ROLI Piano][S22]. Adaptive Press behavior relevant to hardware baseline testing.

**S23.** [MIT License][S23]. Proposed license for original project contributions.

**S24.** [Apple: Gatekeeper and runtime protection][S24]. Installer identity and notarization considerations.

**S25.** [Microsoft Defender SmartScreen][S25]. Application reputation and download warning considerations.

[S01]: https://help.ableton.com/hc/en-us/articles/27303428331420-Ableton-Extensions-FAQ
[S02]: https://ableton.github.io/extensions-sdk/
[S03]: https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts
[S04]: https://docs.cycling74.com/apiref/lom/song/
[S05]: https://docs.cycling74.com/apiref/lom/song_view/
[S06]: https://docs.cycling74.com/apiref/lom/track/
[S07]: https://www.ableton.com/en/live-manual/12/live-concepts/
[S08]: https://www.ableton.com/en/push/manual/
[S09]: https://help.ableton.com/hc/en-us/articles/360019144999-MPE-in-Live-FAQ
[S10]: https://raw.githubusercontent.com/WeAreROLI/roli_blocks_basics/main/LICENSE.txt
[S11]: https://raw.githubusercontent.com/WeAreROLI/roli_blocks_basics/main/protocol/roli_BlocksProtocolDefinitions.h
[S12]: https://raw.githubusercontent.com/WeAreROLI/roli_blocks_basics/main/blocks/roli_BlockConfigId.h
[S13]: https://raw.githubusercontent.com/WeAreROLI/roli_blocks_basics/main/roli_LittleFootFunctions.dox
[S14]: https://raw.githubusercontent.com/WeAreROLI/roli_blocks_basics/main/roli_blocks_basics.h
[S15]: https://forum.juce.com/t/control-lumi-with-block-api/44655
[S16]: https://support.roli.com/en/support/solutions/articles/36000513157-using-piano-m-with-roli-dashboard
[S17]: https://support.roli.com/en/support/solutions/articles/36000584219-roli-piano-faqs
[S18]: https://support.roli.com/en/support/solutions/articles/36000224195-what-is-the-roli-hardware-driver-
[S19]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
[S20]: https://github.com/benob/LUMI-lights
[S21]: https://raw.githubusercontent.com/WeAreROLI/roli_blocks_basics/main/littlefoot/roli_LittleFootCompiler.h
[S22]: https://support.roli.com/en/support/solutions/articles/36000595069-understanding-press-aftertouch-on-roli-piano
[S23]: https://choosealicense.com/licenses/mit/
[S24]: https://support.apple.com/en-sg/guide/security/sec5599b66df/web
[S25]: https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/
