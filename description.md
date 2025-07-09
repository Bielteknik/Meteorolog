Servisin durumu için: sudo systemctl status meteoroloji.service
Servisi durdurmak için: sudo systemctl stop meteoroloji.service
Servisi (tekrar) başlatmak için: sudo systemctl start meteoroloji.service
Kodda bir değişiklik yaptıktan sonra servisi yeniden başlatmak için (en sık kullanacağın): sudo systemctl restart meteoroloji.service
Canlı logları izlemek için: journalctl -u meteoroloji.service -f
----------------------------------------------------------------

