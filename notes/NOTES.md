
 # Log Notes
- Valid response is has the handle of the command sent and nothing else?
- Two commands are sent before most(?) executable command:
    1. `0x02 0x00` with the handle `0x04`
    2. `0x01 0x00` with the handle `0x13`
- All executable commands have the handle `0x10`
- Collected packets in Switch mode (unencrypted):
    * **On** Packet Structure: `0x57 0x01 0x01`
    * **Off** Packet Structure: `0x57 0x01 0x02`
- Collected packets in Switch mode: (encrypted):
    * Change password packet structure (Pass=1234): `0x57 0x17 0xEC 0xE4 0xD0 0x35 0x01 0x04 0x9B 0xE3 0xE0 0xA3 0x00 0x00`  
    * Change password packet structure (Pass=1235): `0x57 0x17 0x9B 0xE3 0xE0 0xA3 0x01 0x04 0xEC 0xE4 0xD0 0x35 0x00 0x00`  
    * **Press** packet structure (Pass=1234):   `0x57 0x11 0x9B 0xE3 0xE0 0xA3`
    * **On** packet structure (Pass=1234):      `0x57 0x12 0x9B 0xE3 0xE0 0xA3 0x01`
    * **Off** packet structure (Pass=1234):     `0x57 0x11 0x9B 0xE3 0xE0 0xA3 0x02`
    * **Press?** packet structure (Pass=1235):   `0x57 0x12 0xEC 0xE4 0xD0 0x35`
- Collected packets when setting a new password (and opening the app):
    * Sync Timer?:  `0x57 0x09 0x01 0x00 0x00 0x00 0x00 0x64 0x14 0xD0 0xA9`
    * Get Settings Packet (sent twice):  `0x57 0x02`
    * Set Password Packet: `0x57 0x07 0x01 0x04 0x9B 0xE3 0xE0 0xA3 0x00 0x00`
    * Press? Packet (with new password): `0x57 0x12 0x9B 0xE3 0xE0 0xA3`


# Information
- Ben's SwitchBot MAC is `F6:9A:4E:9C:3F:3B` with a base nickname of Bot `3B`. I have a theory that multiple prefix bytes are the same between SwitchBots.

# Deduced Packet Structures

## Actions

$$
\begin{align*}
&\begin{array}{|c|c|l|l|c|}
\hline \text { Name } & \text { Handle } & \text { Unencrypted } & \text { Encrypted } & \text { Notes }\\
\hline 
\text{press}    &               & \texttt{0x57 0x01}      & \texttt{0x57 0x11 $\texttt{pw}_8$}       &  \text{This seems to be called at certain times, not sure on the pattern}  \\
\text{turn on}  & \texttt{0x10} & \texttt{0x57 0x01 0x01} & \texttt{0x57 0x11 $\texttt{pw}_8$ 0x01}  &  \text{Sometimes the encrypted 0x11 is a 0x12}                             \\
\text{turn off} &               & \texttt{0x57 0x01 0x02} & \texttt{0x57 0x11 $\texttt{pw}_8$ 0x02}  &                                                                            \\
\hline
\end{array}
\\
\\
&\texttt{pw}_8\text{: crc32 checksum of the password in 4 bytes}
\end{align*}
$$

## Settings

$$
\begin{align*}
&\begin{array}{|c|c|l|l|c|}
\hline \text { Name } & \text { Handle } & \text { Unencrypted } & \text { Encrypted } & \text { Notes }\\
\hline 
\text{set password}     &               & \texttt{0x57 0x07 0x01 0x04 $\texttt{pw-new}_8$ 0x00 0x00}                      &   &                                                              \\
\text{update password}  & \texttt{0x10} & \texttt{0x57 0x17 $\texttt{pw-old}_8$ 0x01 0x04 $\texttt{pw-new}_8$ 0x00 0x00} &   &                                                              \\
\text{get settings}     &               & \texttt{0x57 0x02}                                                               &   &  \text{This is sent twice for some reason during init}       \\
\text{sync timer}       &               & \texttt{0x57 0x09 0x01 $\texttt{t}_{16}$ 0x64 0x14 0xD0 0xA9}                    &   &  \text{Not necsessarily true, $\texttt{t}_{16}$  is 4 zeroed bytes} \\
\hline
\end{array}
\\
\\
&\texttt{pw-new}_8 \text{: crc32 checksum of the new password in 4 bytes} \\
&\texttt{pw-old}_8 \text{: crc32 checksum of the old password in 4 bytes}
\end{align*}
$$
